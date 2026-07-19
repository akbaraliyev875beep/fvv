"""
Tez Yordam EMS — Foydalanuvchi Pydantic Sxemalari

API so'rov/javob validatsiyasi uchun.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Token sxemalari ──────────────────────────────────────────────
class TokenResponse(BaseModel):
    """JWT token juftligi javobi."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token muddati (soniyalarda)")


class TokenRefreshRequest(BaseModel):
    """Token yangilash so'rovi."""
    refresh_token: str


# ── Foydalanuvchi sxemalari ──────────────────────────────────────
class UserBase(BaseModel):
    """Foydalanuvchi bazaviy sxemasi."""
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=9, max_length=20)


class UserUpdate(BaseModel):
    """Foydalanuvchi ma'lumotlarini tahrirlash."""
    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, min_length=9, max_length=20)


class UserRoleUpdate(BaseModel):
    """Foydalanuvchi rolini o'zgartirish."""
    role: str = Field(description="patient / dispatcher / brigade / admin")



class UserRead(BaseModel):
    """Foydalanuvchi o'qish sxemasi."""
    id: uuid.UUID
    full_name: str
    phone: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DispatcherProfileRead(BaseModel):
    """Dispetcher ma'lumotlari."""
    service_type_id: uuid.UUID
    is_on_duty: bool

    model_config = {"from_attributes": True}


class UserWithProfile(UserRead):
    """Foydalanuvchi + bemor/dispetcher profili."""
    # Bemor maydonlari
    blood_type: str | None = None
    allergies: list[str] | None = None
    chronic_conditions: list[str] | None = None
    home_latitude: float | None = None
    home_longitude: float | None = None
    home_address: str | None = None
    
    # Dispetcher maydonlari
    dispatcher_profile: DispatcherProfileRead | None = None


# ── Bemor profili sxemalari ──────────────────────────────────────
class PatientProfileUpdate(BaseModel):
    """Bemor tibbiy ma'lumotlarini yangilash."""
    blood_type: str | None = Field(None, max_length=10, examples=["A+", "B-", "O+"])
    allergies: list[str] | None = Field(None, examples=[["penisilin", "aspirin"]])
    chronic_conditions: list[str] | None = Field(
        None, examples=[["diabet", "gipertenziya"]]
    )
    home_latitude: float | None = Field(None, description="Uyning kengligi")
    home_longitude: float | None = Field(None, description="Uyning uzunligi")
    home_address: str | None = Field(None, max_length=255, description="Uy manzili nomi")


# ── OneID callback ───────────────────────────────────────────────
class OneIDCallbackResponse(BaseModel):
    """OneID muvaffaqiyatli autentifikatsiya javobi."""
    user: UserRead
    tokens: TokenResponse
    is_new_user: bool = Field(description="Yangi ro'yxatdan o'tganmi?")
