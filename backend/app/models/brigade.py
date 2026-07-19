"""
112 Favqulodda Xizmatlar — Brigada Modellari
"""

import enum
import uuid

from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
    Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class BrigadeStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    EN_ROUTE = "en_route"
    OFFLINE = "offline"


class Brigade(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "brigades"

    vehicle_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )
    status: Mapped[BrigadeStatus] = mapped_column(
        Enum(BrigadeStatus, name="brigade_status_enum", create_constraint=True),
        nullable=False,
        default=BrigadeStatus.OFFLINE,
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Xizmat turi (Tez Yordam, O't o'chirish, Militsiya, ...)
    service_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    specialization: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Brigada ixtisoslashuvi, masalan: kardiologiya, qutqaruv",
    )

    service_type: Mapped["ServiceType | None"] = relationship(
        "ServiceType",
        back_populates="brigades",
        lazy="selectin",
    )
    members: Mapped[list["BrigadeMember"]] = relationship(
        "BrigadeMember",
        back_populates="brigade",
        lazy="selectin",
    )
    emergency_calls: Mapped[list["EmergencyCall"]] = relationship(
        "EmergencyCall",
        back_populates="brigade",
        lazy="select",
    )

class BrigadeMember(Base):
    __tablename__ = "brigade_members"

    brigade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brigades.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    brigade: Mapped["Brigade"] = relationship(
        "Brigade",
        back_populates="members",
    )
    user: Mapped["User"] = relationship("User", lazy="selectin")

