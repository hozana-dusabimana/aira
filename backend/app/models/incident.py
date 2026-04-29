from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IncidentStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    verified = "verified"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    severity_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False, length=20),
        nullable=False,
        default=SeverityLevel.medium,
    )
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, length=20),
        nullable=False,
        default=IncidentStatus.pending,
        index=True,
    )
    assigned_officer_id: Mapped[int | None] = mapped_column(
        ForeignKey("officers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("stations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    reporter = relationship("User", back_populates="incidents", foreign_keys=[reporter_id])
    assigned_officer = relationship(
        "Officer", back_populates="assigned_incidents", foreign_keys=[assigned_officer_id]
    )
    station = relationship("Station", back_populates="incidents")
    images = relationship("IncidentImage", back_populates="incident", cascade="all, delete-orphan")
    ai_analysis = relationship(
        "AIAnalysis", back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )
    updates = relationship(
        "IncidentUpdate", back_populates="incident", cascade="all, delete-orphan"
    )
    messages = relationship(
        "FeedbackMessage", back_populates="incident", cascade="all, delete-orphan"
    )
