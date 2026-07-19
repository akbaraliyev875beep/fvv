"""
Tez Yordam EMS — Favqulodda Chaqiruv Modellari
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin


class CallStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EmergencyCall(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "emergency_calls"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    service_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    brigade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brigades.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status_enum", create_constraint=True),
        nullable=False,
        default=CallStatus.PENDING,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    is_multi_service: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    parent_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emergency_calls.id", ondelete="CASCADE"),
        nullable=True,
    )

    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum", create_constraint=True),
        nullable=True,
    )
    risk_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["User"] = relationship("User", back_populates="emergency_calls", lazy="selectin")
    service_type: Mapped["ServiceType | None"] = relationship("ServiceType", back_populates="emergency_calls", lazy="selectin")
    brigade: Mapped["Brigade | None"] = relationship("Brigade", back_populates="emergency_calls", lazy="selectin")
    parent_call: Mapped["EmergencyCall | None"] = relationship("EmergencyCall", remote_side="EmergencyCall.id", back_populates="child_calls")
    child_calls: Mapped[list["EmergencyCall"]] = relationship("EmergencyCall", back_populates="parent_call")
    audio_logs: Mapped[list["CallAudioLog"]] = relationship("CallAudioLog", back_populates="call", lazy="select")


class CallAudioLog(Base, UUIDMixin):
    __tablename__ = "call_audio_logs"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emergency_calls.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    call: Mapped["EmergencyCall"] = relationship("EmergencyCall", back_populates="audio_logs")


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
