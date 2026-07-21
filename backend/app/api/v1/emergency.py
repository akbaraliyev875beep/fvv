"""
Tez Yordam EMS — Favqulodda Chaqiruv (SOS) Router

SOS yaratish, holat kuzatish, status yangilash.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DbSession, DispatcherUser, limiter
from app.models.emergency_call import CallStatus, EmergencyCall, CallAudioLog
from app.models.service_type import ServiceType
from app.models.user import UserRole
from app.schemas.emergency_schema import (
    EmergencyCallList,
    EmergencyCallRead,
    EmergencyStatsResponse,
    SOSCreateRequest,
    SOSCreateResponse,
    StatusUpdateRequest,
)
from app.services.audit_service import log_audit
from app.websockets.connection_manager import manager

logger = logging.getLogger("tez_yordam.emergency")
router = APIRouter()


@router.post("/sos", response_model=SOSCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_sos(
    request: Request,
    body: SOSCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    # Xizmat turlarini aniqlash
    service_types = []
    if body.service_types:
        svc_result = await db.execute(
            select(ServiceType).where(ServiceType.code.in_(body.service_types))
        )
        service_types = svc_result.scalars().all()

    is_multi = len(service_types) > 1

    lat = body.latitude
    lng = body.longitude

    if body.use_home_location:
        from sqlalchemy.orm import selectinload
        user_result = await db.execute(
            select(User).options(selectinload(User.patient_profile)).where(User.id == current_user.id)
        )
        user = user_result.scalar_one()
        if user.patient_profile and user.patient_profile.home_latitude and user.patient_profile.home_longitude:
            lat = user.patient_profile.home_latitude
            lng = user.patient_profile.home_longitude
        else:
            raise HTTPException(status_code=400, detail="Profilingizda uy manzili kiritilmagan.")
    elif lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Joylashuv koordinatalari kiritilishi shart.")

    # Asosiy (parent) chaqiruv yaratish
    parent_call = EmergencyCall(
        patient_id=current_user.id,
        status=CallStatus.PENDING,
        latitude=lat,
        longitude=lng,
        transcript=body.description,
        service_type_id=service_types[0].id if len(service_types) == 1 else None,
        is_multi_service=is_multi,
    )
    db.add(parent_call)
    await db.flush()

    calls_to_broadcast = []
    if is_multi:
        for svc in service_types:
            child_call = EmergencyCall(
                patient_id=current_user.id,
                status=CallStatus.PENDING,
                latitude=lat,
                longitude=lng,
                transcript=body.description,
                service_type_id=svc.id,
                parent_call_id=parent_call.id,
            )
            db.add(child_call)
            calls_to_broadcast.append((child_call, svc.code))
        await db.flush()
    else:
        svc_code = service_types[0].code if service_types else None
        calls_to_broadcast.append((parent_call, svc_code))

    # Audit log
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="sos_created",
        entity_type="emergency_call",
        entity_id=str(parent_call.id),
        ip_address=request.client.host if request.client else None,
    )

    # WebSocket orqali dispetcherlarga xabar yuborish
    for call_obj, svc_code in calls_to_broadcast:
        await manager.broadcast_to_dispatchers({
            "type": "new_sos",
            "call_id": str(call_obj.id),
            "patient_name": current_user.full_name,
            "latitude": lat,
            "longitude": lng,
            "description": body.description,
            "service_type": svc_code,
            "is_multi_service": call_obj.is_multi_service or (call_obj.parent_call_id is not None),
            "status": CallStatus.PENDING.value,
            "created_at": call_obj.created_at.isoformat() if call_obj.created_at else datetime.now(timezone.utc).isoformat(),
        }, service_type_code=svc_code)

    logger.info(f"🆘 Yangi SOS chaqiruv: {parent_call.id} — bemor: {current_user.full_name}, xizmatlar: {[s.code for s in service_types] or 'umumiy'}")

    return SOSCreateResponse(
        call_id=parent_call.id,
        status=CallStatus.PENDING.value,
    )


@router.post("/sos/audio/{call_id}")
@limiter.limit("3/minute")
async def upload_audio(
    request: Request,
    call_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    audio: UploadFile = File(...),
):
    """
    SOS chaqiruvga ovozli xabar qo'shish.

    Audio fayl vaqtinchalik saqlanadi va Whisper STT uchun navbatga qo'yiladi.
    """
    # Chaqiruvni tekshirish
    result = await db.execute(
        select(EmergencyCall).where(
            EmergencyCall.id == call_id,
            EmergencyCall.patient_id == current_user.id,
        )
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )

    # Audio faylni vaqtinchalik saqlash
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp(prefix="tez_yordam_audio_")
    file_path = os.path.join(temp_dir, f"{call_id}_{audio.filename}")

    content = await audio.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Audio log yaratish
    audio_log = CallAudioLog(
        call_id=call_id,
        storage_path=file_path,
        duration_sec=None,  # Keyinroq hisoblash mumkin
    )
    db.add(audio_log)
    await db.flush()

    logger.info(f"🎙️ Audio yuklandi: call={call_id}, fayl={audio.filename}")

    return {
        "detail": "Audio muvaffaqiyatli yuklandi",
        "audio_log_id": str(audio_log.id),
        "call_id": str(call_id),
    }


@router.get("/stats", response_model=EmergencyStatsResponse)
async def get_emergency_stats(
    current_user: DispatcherUser,
    db: DbSession,
):
    """Tizim statistikasi (Admin/Dispatcher)."""
    from datetime import datetime, timezone, timedelta
    from app.models.brigade import Brigade, BrigadeStatus
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Bugungi chaqiruvlar
    calls_today_res = await db.execute(
        select(func.count(EmergencyCall.id)).where(EmergencyCall.created_at >= today_start)
    )
    total_calls_today = calls_today_res.scalar() or 0
    
    # Faol chaqiruvlar
    active_res = await db.execute(
        select(func.count(EmergencyCall.id)).where(
            EmergencyCall.status.in_([CallStatus.PENDING, CallStatus.ASSIGNED, CallStatus.EN_ROUTE, CallStatus.ARRIVED])
        )
    )
    active_calls = active_res.scalar() or 0
    
    # Bo'sh brigadalar
    brigades_res = await db.execute(
        select(func.count(Brigade.id)).where(Brigade.status == BrigadeStatus.AVAILABLE)
    )
    available_brigades = brigades_res.scalar() or 0
    
    # O'rtacha javob vaqti (pending -> assigned) bugun uchun
    avg_res = await db.execute(
        select(func.avg(func.extract('epoch', EmergencyCall.assigned_at - EmergencyCall.created_at)))
        .where(
            EmergencyCall.created_at >= today_start,
            EmergencyCall.assigned_at.isnot(None)
        )
    )
    avg_seconds = avg_res.scalar() or 0
    avg_minutes = round(avg_seconds / 60.0, 1) if avg_seconds > 0 else 0
    
    return EmergencyStatsResponse(
        total_calls_today=total_calls_today,
        active_calls=active_calls,
        available_brigades=available_brigades,
        average_response_time_mins=avg_minutes,
    )


@router.get("/{call_id}", response_model=EmergencyCallRead)
async def get_emergency_call(
    call_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Chaqiruv ma'lumotlarini olish.

    Bemor faqat o'z chaqiruvini, dispetcher barcha chaqiruvlarni ko'ra oladi.
    """
    query = select(EmergencyCall).where(EmergencyCall.id == call_id)

    # Bemor faqat o'z chaqiruvini ko'radi
    if current_user.role == UserRole.PATIENT:
        query = query.where(EmergencyCall.patient_id == current_user.id)

    result = await db.execute(query)
    call = result.scalar_one_or_none()

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )

    return _call_to_response(call)


@router.get("/active/list", response_model=EmergencyCallList)
async def list_active_calls(
    current_user: DispatcherUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
    service_type: str | None = None,
):
    """
    Barcha faol chaqiruvlar ro'yxati (faqat dispetcher/admin).

    service_type parametri orqali xizmat turiga qarab filter qilish mumkin.
    """
    active_statuses = [CallStatus.PENDING, CallStatus.ASSIGNED, CallStatus.EN_ROUTE, CallStatus.ARRIVED]

    # Asosiy shart
    filters = [
        EmergencyCall.status.in_(active_statuses),
        EmergencyCall.deleted_at.is_(None),
    ]

    # Xizmat turi bo'yicha filter
    if service_type:
        svc_result = await db.execute(
            select(ServiceType).where(ServiceType.code == service_type)
        )
        svc = svc_result.scalar_one_or_none()
        if svc:
            filters.append(EmergencyCall.service_type_id == svc.id)

    # Umumiy son
    count_result = await db.execute(
        select(func.count(EmergencyCall.id)).where(*filters)
    )
    total = count_result.scalar() or 0

    # Chaqiruvlar
    result = await db.execute(
        select(EmergencyCall)
        .where(*filters)
        .order_by(desc(EmergencyCall.created_at))
        .offset(skip)
        .limit(limit)
    )
    calls = result.scalars().all()

    return EmergencyCallList(
        total=total,
        items=[_call_to_response(c) for c in calls],
    )


@router.patch("/{call_id}/status", response_model=EmergencyCallRead)
async def update_call_status(
    request: Request,
    call_id: uuid.UUID,
    body: StatusUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Chaqiruv statusini yangilash.

    Dispetcher: assigned qiladi.
    Brigada: en_route, arrived, completed qiladi.
    """
    result = await db.execute(
        select(EmergencyCall).where(EmergencyCall.id == call_id)
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )

    # Status o'zgartirish
    new_status = CallStatus(body.status)
    old_status = call.status
    call.status = new_status

    if new_status == CallStatus.ASSIGNED and body.brigade_id:
        call.brigade_id = body.brigade_id
        call.assigned_at = datetime.now(timezone.utc)

    if new_status in (CallStatus.COMPLETED, CallStatus.CANCELLED):
        call.resolved_at = datetime.now(timezone.utc)

    await db.flush()

    # Audit log
    await log_audit(
        db=db,
        user_id=current_user.id,
        action=f"status_changed_{old_status.value}_to_{new_status.value}",
        entity_type="emergency_call",
        entity_id=str(call.id),
        ip_address=request.client.host if request.client else None,
    )

    # WebSocket xabar
    ws_message = {
        "type": "status_update",
        "call_id": str(call.id),
        "old_status": old_status.value,
        "new_status": new_status.value,
        "brigade_id": str(call.brigade_id) if call.brigade_id else None,
    }
    await manager.broadcast_to_dispatchers(ws_message)
    await manager.send_to_patient(str(call.id), ws_message)
    if call.brigade_id:
        await manager.send_to_brigade(str(call.brigade_id), ws_message)

    logger.info(f"📋 Status yangilandi: call={call.id} {old_status.value}→{new_status.value}")

    return _call_to_response(call)


def _call_to_response(call: EmergencyCall) -> EmergencyCallRead:
    """EmergencyCall modelini EmergencyCallRead sxemasiga o'girish."""
    return EmergencyCallRead(
        id=call.id,
        patient_id=call.patient_id,
        patient_name=call.patient.full_name if call.patient else None,
        patient_phone=call.patient.phone if call.patient else None,
        brigade_id=call.brigade_id,
        brigade_vehicle=call.brigade.vehicle_number if call.brigade else None,
        service_type_id=call.service_type_id,
        is_multi_service=call.is_multi_service,
        parent_call_id=call.parent_call_id,
        status=call.status.value,
        latitude=call.latitude,
        longitude=call.longitude,
        transcript=call.transcript,
        risk_level=call.risk_level.value if call.risk_level else None,
        risk_confidence=call.risk_confidence,
        recommended_action=call.recommended_action,
        created_at=call.created_at,
        assigned_at=call.assigned_at,
        resolved_at=call.resolved_at,
    )


@router.get("/history", response_model=EmergencyCallList)
async def get_call_history(
    current_user: CurrentUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    """Foydalanuvchining chaqiruvlar tarixi."""
    query = select(EmergencyCall)
    if current_user.role == UserRole.PATIENT:
        query = query.where(EmergencyCall.patient_id == current_user.id)
    
    query = query.where(EmergencyCall.deleted_at.is_(None))
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    
    result = await db.execute(
        query.order_by(desc(EmergencyCall.created_at)).offset(skip).limit(limit)
    )
    calls = result.scalars().all()
    
    return EmergencyCallList(
        total=total,
        items=[_call_to_response(c) for c in calls]
    )




@router.delete("/{call_id}/cancel")
async def cancel_emergency_call(
    call_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Chaqiruvni bekor qilish."""
    result = await db.execute(
        select(EmergencyCall).where(EmergencyCall.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if call is None:
        raise HTTPException(status_code=404, detail="Chaqiruv topilmadi")
        
    if current_user.role == UserRole.PATIENT and call.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
        
    if call.status in [CallStatus.COMPLETED, CallStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Chaqiruv allaqachon yakunlangan yoki bekor qilingan")
        
    call.status = CallStatus.CANCELLED
    call.resolved_at = datetime.now(timezone.utc)
    
    if call.brigade_id:
        from app.models.brigade import Brigade, BrigadeStatus
        b_res = await db.execute(select(Brigade).where(Brigade.id == call.brigade_id))
        brigade = b_res.scalar_one_or_none()
        if brigade:
            brigade.status = BrigadeStatus.AVAILABLE
            
    await db.flush()
    
    ws_message = {
        "type": "status_update",
        "call_id": str(call.id),
        "old_status": call.status.value,
        "new_status": CallStatus.CANCELLED.value,
    }
    await manager.broadcast_to_dispatchers(ws_message)
    
    return {"detail": "Chaqiruv bekor qilindi"}
