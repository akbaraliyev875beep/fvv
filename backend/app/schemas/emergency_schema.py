"""
Tez Yordam EMS — Favqulodda Chaqiruv Pydantic Sxemalari
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── SOS yaratish ─────────────────────────────────────────────────
class SOSCreateRequest(BaseModel):
    """SOS chaqiruv yaratish so'rovi."""
    latitude: float | None = Field(None, ge=-90, le=90, description="Kenglik")
    longitude: float | None = Field(None, ge=-180, le=180, description="Uzunlik")
    use_home_location: bool = Field(False, description="Bemorning profilidagi uy manzilidan foydalanish")
    description: str | None = Field(
        None,
        max_length=1000,
        description="Qisqa tavsif (ixtiyoriy)",
    )
    service_types: list[str] | None = Field(
        None,
        description="Xizmat kodlari ro'yxati, masalan: ['ambulance', 'fire']. Agar bo'sh bo'lsa AI aniqlaydi",
    )


class SOSCreateResponse(BaseModel):
    """SOS chaqiruv yaratilgandan keyingi javob."""
    call_id: uuid.UUID
    status: str
    message: str = "SOS chaqiruvingiz qabul qilindi. Tez orada yordam keladi!"


# ── Chaqiruv holati ──────────────────────────────────────────────
class EmergencyCallRead(BaseModel):
    """Chaqiruv to'liq ma'lumoti."""
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str | None = None
    patient_phone: str | None = None
    brigade_id: uuid.UUID | None = None
    brigade_vehicle: str | None = None
    service_type_id: uuid.UUID | None = None
    is_multi_service: bool = False
    parent_call_id: uuid.UUID | None = None
    status: str
    latitude: float | None = None
    longitude: float | None = None
    transcript: str | None = None
    risk_level: str | None = None
    risk_confidence: float | None = None
    recommended_action: str | None = None
    created_at: datetime
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class StatusUpdateRequest(BaseModel):
    """Chaqiruv statusini yangilash."""
    status: str = Field(
        description="Yangi status: assigned, en_route, arrived, completed, cancelled"
    )
    brigade_id: uuid.UUID | None = Field(
        None,
        description="Tayinlanadigan brigada ID (faqat assigned statusi uchun)",
    )


# ── Risk Score ───────────────────────────────────────────────────
class RiskScoreRequest(BaseModel):
    """Risk score hisoblash so'rovi."""
    transcript: str = Field(min_length=5, description="Transkripsiya matni")
    age: int | None = Field(None, ge=0, le=150, description="Bemor yoshi")
    gender: str | None = Field(None, description="Jinsi (male/female)")
    chief_complaint: str | None = Field(None, description="Asosiy shikoyat")


class RiskScoreResponse(BaseModel):
    """Risk score natijasi."""
    risk_level: str = Field(description="LOW / MEDIUM / HIGH / CRITICAL")
    confidence_score: float = Field(ge=0, le=1, description="Ishonch darajasi")
    recommended_action: str = Field(description="Tavsiya qilingan harakat")
    reasoning: str = Field(description="AI izohi")
    recommended_services: list[str] = Field(default_factory=list, description="Tavsiya qilingan xizmat kodlari")


# ── Ro'yxat uchun ────────────────────────────────────────────────
class EmergencyCallList(BaseModel):
    """Chaqiruvlar ro'yxati (paginated)."""
    total: int
    items: list[EmergencyCallRead]


class EmergencyStatsResponse(BaseModel):
    """Tizim statistikasi."""
    total_calls_today: int
    active_calls: int
    available_brigades: int
    average_response_time_mins: float | None = None
