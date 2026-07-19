"""
112 Favqulodda Xizmatlar — Xizmat Turi Modeli

Barcha favqulodda xizmat turlari: Tez Yordam, O't o'chirish, Militsiya, FVV, Gaz.
"""

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class ServiceType(Base, UUIDMixin, TimestampMixin):
    """Favqulodda xizmat turlari jadvali."""

    __tablename__ = "service_types"

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="Xizmat kodi: ambulance, fire, police, fvv, gas",
    )
    name_uz: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="O'zbekcha nomi",
    )
    name_ru: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Ruscha nomi",
    )
    phone_number: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Qo'ng'iroq raqami (103, 101, ...)",
    )
    color_hex: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="#EF4444",
        comment="Xizmat rangi (HEX)",
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="fa-solid fa-phone",
        comment="FontAwesome ikon klassi",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Xizmat faolmi?",
    )

    # Munosabatlar
    brigades: Mapped[list["Brigade"]] = relationship(
        "Brigade",
        back_populates="service_type",
        lazy="select",
    )
    emergency_calls: Mapped[list["EmergencyCall"]] = relationship(
        "EmergencyCall",
        back_populates="service_type",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ServiceType {self.code}: {self.name_uz}>"
