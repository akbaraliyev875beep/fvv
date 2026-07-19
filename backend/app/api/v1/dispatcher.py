"""
Tez Yordam EMS — Dispetcher Router

Eng yaqin brigadalar, brigada tayinlash, dashboard.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status


from sqlalchemy import select, cast, Float, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DbSession, DispatcherUser
from app.models.brigade import Brigade, BrigadeStatus
from app.models.emergency_call import EmergencyCall, CallStatus
from app.schemas.brigade_schema import (
    BrigadeAssignRequest,
    BrigadeLocationUpdate,
    BrigadeRead,
    BrigadeStatusUpdate,
    NearbyBrigadesRequest,
    BrigadeCreate,
    BrigadeUpdate,
)
from app.services.audit_service import log_audit
from app.websockets.connection_manager import manager

logger = logging.getLogger("tez_yordam.dispatcher")
router = APIRouter()


@router.get("/brigades/nearby", response_model=list[BrigadeRead])
async def get_nearby_brigades(
    current_user: DispatcherUser,
    db: DbSession,
    latitude: float,
    longitude: float,
    radius_km: float = 50.0,
    limit: int = 10,
    service_type_id: uuid.UUID | None = None,
):
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0 # Yer radiusi km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    query = select(Brigade).where(Brigade.status == BrigadeStatus.AVAILABLE)
    if service_type_id:
        query = query.where(Brigade.service_type_id == service_type_id)

    result = await db.execute(query)
    all_brigades = result.scalars().all()

    nearby = []
    for b in all_brigades:
        if b.latitude is not None and b.longitude is not None:
            dist = haversine(latitude, longitude, b.latitude, b.longitude)
            if dist <= radius_km:
                nearby.append((b, dist))

    nearby.sort(key=lambda x: x[1])
    nearby = nearby[:limit]

    return [
        BrigadeRead(
            id=b.id,
            vehicle_number=b.vehicle_number,
            status=b.status.value,
            service_type_id=b.service_type_id,
            specialization=b.specialization,
            latitude=b.latitude,
            longitude=b.longitude,
            distance_km=round(dist, 2),
            updated_at=b.updated_at,
        )
        for b, dist in nearby
    ]


@router.post("/assign")
async def assign_brigade(
    request: Request,
    body: BrigadeAssignRequest,
    current_user: DispatcherUser,
    db: DbSession,
):
    """
    Brigadani chaqiruvga tayinlash.

    1. Brigada mavjudligini tekshiradi
    2. Chaqiruv statusini `assigned` qiladi
    3. Brigada statusini `en_route` ga o'zgartiradi
    4. Audit log va WebSocket xabar yuboradi
    """
    # Brigadani tekshirish
    brigade_result = await db.execute(
        select(Brigade).where(Brigade.id == body.brigade_id)
    )
    brigade = brigade_result.scalar_one_or_none()
    if brigade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brigada topilmadi",
        )
    if brigade.status != BrigadeStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brigada hozir band ({brigade.status.value})",
        )

    # Chaqiruvni tekshirish
    call_result = await db.execute(
        select(EmergencyCall).where(EmergencyCall.id == body.call_id)
    )
    call = call_result.scalar_one_or_none()
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )
    if call.status != CallStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Chaqiruv allaqachon tayinlangan ({call.status.value})",
        )

    if call.service_type_id and brigade.service_type_id and call.service_type_id != brigade.service_type_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brigada va chaqiruv xizmat turlari mos emas",
        )

    # Tayinlash
    from datetime import datetime, timezone
    call.brigade_id = brigade.id
    call.status = CallStatus.ASSIGNED
    call.assigned_at = datetime.now(timezone.utc)
    brigade.status = BrigadeStatus.EN_ROUTE

    await db.flush()

    # Audit log
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="brigade_assigned",
        entity_type="emergency_call",
        entity_id=str(call.id),
        ip_address=request.client.host if request.client else None,
        details=f"brigade_id={brigade.id}",
    )

    # WebSocket xabarlar
    ws_message = {
        "type": "brigade_assigned",
        "call_id": str(call.id),
        "brigade_id": str(brigade.id),
        "brigade_vehicle": brigade.vehicle_number,
        "status": CallStatus.ASSIGNED.value,
    }
    await manager.broadcast_to_dispatchers(ws_message)
    await manager.send_to_patient(str(call.id), ws_message)
    await manager.send_to_brigade(str(brigade.id), ws_message)

    logger.info(f"🚑 Brigada tayinlandi: call={call.id} → brigade={brigade.id}")

    return {
        "detail": "Brigada muvaffaqiyatli tayinlandi",
        "call_id": str(call.id),
        "brigade_id": str(brigade.id),
    }


@router.patch("/brigades/{brigade_id}/location")
async def update_brigade_location(
    brigade_id: uuid.UUID,
    body: BrigadeLocationUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Brigada joylashuvini yangilash (GPS tracking)."""
    result = await db.execute(
        select(Brigade).where(Brigade.id == brigade_id)
    )
    brigade = result.scalar_one_or_none()
    if brigade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brigada topilmadi",
        )

    brigade.latitude = body.latitude
    brigade.longitude = body.longitude
    await db.flush()

    # Dispetcherlarga real-time joylashuv
    await manager.broadcast_to_dispatchers({
        "type": "brigade_location",
        "brigade_id": str(brigade_id),
        "latitude": body.latitude,
        "longitude": body.longitude,
        "vehicle_number": brigade.vehicle_number,
    })

    return {"detail": "Joylashuv yangilandi"}


@router.patch("/brigades/{brigade_id}/status")
async def update_brigade_status(
    brigade_id: uuid.UUID,
    body: BrigadeStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Brigada holatini yangilash."""
    result = await db.execute(
        select(Brigade).where(Brigade.id == brigade_id)
    )
    brigade = result.scalar_one_or_none()
    if brigade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brigada topilmadi",
        )

    brigade.status = BrigadeStatus(body.status)
    await db.flush()

    await manager.broadcast_to_dispatchers({
        "type": "brigade_status",
        "brigade_id": str(brigade_id),
        "status": body.status,
        "vehicle_number": brigade.vehicle_number,
    })
    return {"detail": f"Brigada holati yangilandi: {body.status}"}


# --- Brigadalar CRUD (Admin) ---

from app.core.dependencies import AdminUser

@router.get("/brigades", response_model=list[BrigadeRead])
async def list_brigades(
    current_user: DispatcherUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    """Barcha brigadalar ro'yxati."""
    result = await db.execute(select(Brigade).order_by(Brigade.created_at.desc()).offset(skip).limit(limit))
    brigades = result.scalars().all()
    return [BrigadeRead.model_validate(b) for b in brigades]


@router.post("/brigades", response_model=BrigadeRead, status_code=status.HTTP_201_CREATED)
async def create_brigade(
    body: BrigadeCreate,
    current_user: AdminUser,
    db: DbSession,
):
    """Yangi brigada qo'shish (Faqat Admin)."""
    # Tekshirish
    result = await db.execute(select(Brigade).where(Brigade.vehicle_number == body.vehicle_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bunday raqamli avtomobil mavjud")
        
    brigade = Brigade(
        vehicle_number=body.vehicle_number,
        status=BrigadeStatus(body.status) if body.status else BrigadeStatus.OFFLINE,
        service_type_id=body.service_type_id,
        specialization=body.specialization,
    )
    db.add(brigade)
    await db.flush()
    return BrigadeRead.model_validate(brigade)


@router.put("/brigades/{brigade_id}", response_model=BrigadeRead)
async def update_brigade(
    brigade_id: uuid.UUID,
    body: BrigadeUpdate,
    current_user: AdminUser,
    db: DbSession,
):
    """Brigada ma'lumotlarini tahrirlash (Faqat Admin)."""
    result = await db.execute(select(Brigade).where(Brigade.id == brigade_id))
    brigade = result.scalar_one_or_none()
    
    if not brigade:
        raise HTTPException(status_code=404, detail="Brigada topilmadi")
        
    if body.vehicle_number is not None:
        # Check uniqueness
        check_res = await db.execute(
            select(Brigade).where(Brigade.vehicle_number == body.vehicle_number, Brigade.id != brigade_id)
        )
        if check_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bunday raqamli avtomobil mavjud")
        brigade.vehicle_number = body.vehicle_number
        
    if body.status is not None:
        brigade.status = BrigadeStatus(body.status)

    if body.service_type_id is not None:
        brigade.service_type_id = body.service_type_id

    if body.specialization is not None:
        brigade.specialization = body.specialization
        
    await db.flush()
    return BrigadeRead.model_validate(brigade)


@router.delete("/brigades/{brigade_id}")
async def delete_brigade(
    brigade_id: uuid.UUID,
    current_user: AdminUser,
    db: DbSession,
):
    """Brigadani o'chirish (Faqat Admin)."""
    result = await db.execute(select(Brigade).where(Brigade.id == brigade_id))
    brigade = result.scalar_one_or_none()
    
    if not brigade:
        raise HTTPException(status_code=404, detail="Brigada topilmadi")
        
    await db.delete(brigade)
    await db.flush()
    return {"detail": "Brigada o'chirildi"}
