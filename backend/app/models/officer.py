from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Officer(Base):
    __tablename__ = "officers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    badge_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("stations.id", ondelete="SET NULL"), nullable=True
    )
    rank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="officer")
    station = relationship("Station", back_populates="officers")
    assigned_incidents = relationship(
        "Incident", back_populates="assigned_officer", foreign_keys="Incident.assigned_officer_id"
    )
