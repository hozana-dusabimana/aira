from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    officer_id: Mapped[int | None] = mapped_column(
        ForeignKey("officers.id", ondelete="SET NULL"), nullable=True
    )
    update_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_change: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    incident = relationship("Incident", back_populates="updates")
