"""
112 Favqulodda Xizmatlar — Xizmat Turlari Router

Barcha xizmat turlarini olish va boshqarish.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, AdminUser, DispatcherUser
from app.models.service_type import ServiceType
from app.schemas.service_type_schema import (
    ServiceTypeCreate,
    ServiceTypeRead,
    ServiceTypeUpdate,
)

logger = logging.getLogger("tez_yordam.services")
router = APIRouter()


@router.get("/", response_model=list[ServiceTypeRead])
async def list_service_types(
    db: DbSession,
):
    """
    Barcha faol xizmat turlari ro'yxati.

    Bu endpoint autentifikatsiya talab qilmaydi — SOS sahifasida
    foydalanuvchi xizmat turlarini ko'rishi kerak.
    """
    result = await db.execute(
        select(ServiceType)
        .where(ServiceType.is_active == True)
        .order_by(ServiceType.phone_number)
    )
    services = result.scalars().all()
    return [ServiceTypeRead.model_validate(s) for s in services]


@router.get("/all", response_model=list[ServiceTypeRead])
async def list_all_service_types(
    current_user: AdminUser,
    db: DbSession,
):
    """
    Barcha xizmat turlari ro'yxati (faol va nofaol).
    Faqat Admin uchun.
    """
    result = await db.execute(
        select(ServiceType).order_by(ServiceType.phone_number)
    )
    services = result.scalars().all()
    return [ServiceTypeRead.model_validate(s) for s in services]


@router.get("/{code}", response_model=ServiceTypeRead)
async def get_service_type(
    code: str,
    db: DbSession,
):
    """
    Bitta xizmat turi ma'lumotlari (kod bo'yicha).

    Masalan: /api/v1/services/ambulance
    """
    result = await db.execute(
        select(ServiceType).where(ServiceType.code == code)
    )
    service = result.scalar_one_or_none()

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{code}' kodli xizmat turi topilmadi",
        )

    return ServiceTypeRead.model_validate(service)


@router.post("/", response_model=ServiceTypeRead, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    body: ServiceTypeCreate,
    current_user: AdminUser,
    db: DbSession,
):
    """Yangi xizmat turi qo'shish (Faqat Admin)."""
    # Kod unikal ekanligini tekshirish
    existing = await db.execute(
        select(ServiceType).where(ServiceType.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{body.code}' kodli xizmat turi allaqachon mavjud",
        )

    service = ServiceType(**body.model_dump())
    db.add(service)
    await db.flush()

    logger.info(f"✅ Yangi xizmat turi yaratildi: {service.code}")
    return ServiceTypeRead.model_validate(service)


@router.put("/{service_id}", response_model=ServiceTypeRead)
async def update_service_type(
    service_id: uuid.UUID,
    body: ServiceTypeUpdate,
    current_user: AdminUser,
    db: DbSession,
):
    """Xizmat turini tahrirlash (Faqat Admin)."""
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_id)
    )
    service = result.scalar_one_or_none()

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xizmat turi topilmadi",
        )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)

    await db.flush()
    logger.info(f"📝 Xizmat turi yangilandi: {service.code}")
    return ServiceTypeRead.model_validate(service)


@router.delete("/{service_id}")
async def delete_service_type(
    service_id: uuid.UUID,
    current_user: AdminUser,
    db: DbSession,
):
    """Xizmat turini o'chirish (Faqat Admin)."""
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_id)
    )
    service = result.scalar_one_or_none()

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xizmat turi topilmadi",
        )

    # Soft delete — faolsizlantirish
    service.is_active = False
    await db.flush()

    logger.info(f"🗑️ Xizmat turi faolsizlantirildi: {service.code}")
    return {"detail": f"'{service.code}' xizmat turi faolsizlantirildi"}
