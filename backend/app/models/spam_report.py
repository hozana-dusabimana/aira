from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpamReport(Base):
    """Quarantine record for a submission the AI rejected as a non-incident.

    Rather than silently deleting rejected uploads, we move the image into the
    ``uploads/spam/`` folder and keep a lightweight record here. This preserves
    an audit trail (abuse / repeat false reports) and a recovery path if the AI
    wrongly rejected a genuine emergency. ``incident_id`` is stored as a plain
    integer (not a foreign key) because the originating incident row may be
    deleted in the synchronous path.
    """

    __tablename__ = "spam_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # The original incident id, kept for reference. No FK: the incident row may
    # be gone (sync path deletes it after rejection).
    incident_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    incident_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # When reason == "duplicate", the id of the existing incident this report
    # duplicates (the first report of the same accident). Plain integer, no FK:
    # mirrors ``incident_id`` and survives the original being deleted.
    duplicate_of_incident_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    ai_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    reporter = relationship("User", foreign_keys=[reporter_id])
