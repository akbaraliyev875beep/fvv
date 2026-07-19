"""
Tez Yordam EMS — Brigada Pydantic Sxemalari
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BrigadeCreate(BaseModel):
    """Yangi brigada yaratish."""
    vehicle_number: str = Field(min_length=3, max_length=20)
    status: str | None = Field("offline", description="available / busy / en_route / offline")
    service_type_id: uuid.UUID | None = None
    specialization: str | None = Field(None, max_length=100)


class BrigadeUpdate(BaseModel):
    """Brigada tahrirlash."""
    vehicle_number: str | None = Field(None, min_length=3, max_length=20)
    status: str | None = Field(None, description="available / busy / en_route / offline")
    service_type_id: uuid.UUID | None = None
    specialization: str | None = Field(None, max_length=100)


class BrigadeRead(BaseModel):
    """Brigada o'qish sxemasi."""
    id: uuid.UUID
    vehicle_number: str
    status: str
    service_type_id: uuid.UUID | None = None
    specialization: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = Field(None, description="Bemorga masofa (km)")
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrigadeLocationUpdate(BaseModel):
    """Brigada joylashuvini yangilash."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class BrigadeStatusUpdate(BaseModel):
    """Brigada holatini yangilash."""
    status: str = Field(description="available / busy / en_route / offline")


class BrigadeAssignRequest(BaseModel):
    """Brigadani chaqiruvga tayinlash."""
    call_id: uuid.UUID
    brigade_id: uuid.UUID


class NearbyBrigadesRequest(BaseModel):
    """Eng yaqin brigadalarni qidirish."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=50.0, ge=1, le=200, description="Qidiruv radiusi (km)")
    limit: int = Field(default=10, ge=1, le=50)
