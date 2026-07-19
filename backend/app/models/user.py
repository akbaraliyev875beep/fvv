"""
Tez Yordam EMS — Foydalanuvchi va Bemor Modellari

users jadvali — barcha foydalanuvchilar (patient, dispatcher, brigade, admin)
patients jadvali — bemorlarning tibbiy ma'lumotlari (1:1 users bilan)
"""

import enum
import uuid

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin


class UserRole(str, enum.Enum):
    """Foydalanuvchi rollari."""
    PATIENT = "patient"
    DISPATCHER = "dispatcher"
    BRIGADE = "brigade"
    ADMIN = "admin"


class User(Base, UUIDMixin, TimestampMixin):
    """Foydalanuvchilar jadvali."""

    __tablename__ = "users"

    oneid_pin: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="OneID PIN (AES-256 bilan shifrlangan)",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_constraint=True),
        nullable=False,
        default=UserRole.PATIENT,
    )

    # Munosabatlar
    patient_profile: Mapped["Patient | None"] = relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    dispatcher_profile: Mapped["Dispatcher | None"] = relationship(
        "Dispatcher",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    emergency_calls: Mapped[list["EmergencyCall"]] = relationship(
        "EmergencyCall",
        back_populates="patient",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User {self.full_name} ({self.role.value})>"


class Patient(Base, SoftDeleteMixin):
    """Bemorlarning tibbiy ma'lumotlari — users bilan 1:1."""

    __tablename__ = "patients"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blood_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Qon guruhi (masalan: A+, B-, O+)",
    )
    allergies: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Allergiyalar ro'yxati",
    )
    chronic_conditions: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Surunkali kasalliklar ro'yxati",
    )
    home_latitude: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Uyning kengligi (latitude)",
    )
    home_longitude: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Uyning uzunligi (longitude)",
    )
    home_address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Uy manzili nomi/matni",
    )

    # Munosabat
    user: Mapped["User"] = relationship(
        "User",
        back_populates="patient_profile",
    )

    def __repr__(self) -> str:
        return f"<Patient user_id={self.user_id}>"


class Dispatcher(Base, SoftDeleteMixin):
    """Dispetcher profili — users bilan 1:1, qaysi xizmatga tegishliligini bildiradi."""

    __tablename__ = "dispatchers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    service_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_on_duty: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    # Munosabatlar
    user: Mapped["User"] = relationship(
        "User",
        back_populates="dispatcher_profile",
    )
    service_type: Mapped["ServiceType"] = relationship(
        "ServiceType",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Dispatcher user_id={self.user_id} service_type_id={self.service_type_id}>"
