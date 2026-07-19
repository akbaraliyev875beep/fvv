"""
Tez Yordam EMS — Service Type Pydantic Sxemalari
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ServiceTypeBase(BaseModel):
    """Xizmat turi bazaviy sxemasi."""
    code: str = Field(min_length=2, max_length=30, examples=["ambulance", "fire"])
    name_uz: str = Field(min_length=2, max_length=100)
    name_ru: str = Field(min_length=2, max_length=100)
    phone_number: str = Field(min_length=3, max_length=10)
    color_hex: str = Field(default="#EF4444", max_length=10)
    icon: str = Field(default="fa-solid fa-phone", max_length=50)
    is_active: bool = True


class ServiceTypeCreate(ServiceTypeBase):
    """Yangi xizmat turi yaratish."""
    pass


class ServiceTypeUpdate(BaseModel):
    """Xizmat turini tahrirlash."""
    code: str | None = Field(None, min_length=2, max_length=30)
    name_uz: str | None = Field(None, min_length=2, max_length=100)
    name_ru: str | None = Field(None, min_length=2, max_length=100)
    phone_number: str | None = Field(None, min_length=3, max_length=10)
    color_hex: str | None = Field(None, max_length=10)
    icon: str | None = Field(None, max_length=50)
    is_active: bool | None = None


class ServiceTypeRead(ServiceTypeBase):
    """Xizmat turini o'qish."""
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
