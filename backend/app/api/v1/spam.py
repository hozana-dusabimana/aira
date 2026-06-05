import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import require_admin, require_officer
from app.database import get_db
from app.models.incident import Incident, IncidentStatus, SeverityLevel
from app.models.incident_image import IncidentImage
from app.models.spam_report import SpamReport
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.incident import IncidentOut
from app.schemas.spam import SpamOut
from app.services.ai_service import (
    delete_upload_file,
    emit_incident_event,
    notify_officers_new_incident,
)
from app.services.file_service import unquarantine_upload_file
from app.services.notification_service import create_notification

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/", response_model=list[SpamOut])
def list_spam(
    _: Annotated[User, Depends(require_officer)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SpamReport]:
    """List quarantined (rejected) reports for the dashboard Spam page."""
    stmt = (
        select(SpamReport)
        .options(selectinload(SpamReport.reporter))
        .order_by(SpamReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


@router.post("/{spam_id}/not-spam", response_model=IncidentOut)
def mark_not_spam(
    spam_id: int,
    _: Annotated[User, Depends(require_officer)],
    db: Annotated[Session, Depends(get_db)],
) -> Incident:
    """Restore a spam report as a real incident.

    Moves the image back out of the spam folder, re-activates (or recreates)
    the incident with status ``verified``, notifies officers + the reporter,
    broadcasts the new incident and removes the spam record.
    """
    spam = db.get(SpamReport, spam_id)
    if not spam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spam report not found")

    restored_url = unquarantine_upload_file(spam.image_url) or spam.image_url

    incident = db.get(Incident, spam.incident_id) if spam.incident_id else None
    if incident is not None:
        # Async path kept the rejected row — just re-activate it.
        incident.status = IncidentStatus.verified
        incident.image_url = restored_url
        if spam.incident_type:
            incident.incident_type = spam.incident_type
        if spam.ai_description:
            incident.ai_description = spam.ai_description
        db.commit()
    else:
        # Sync path deleted the original row — recreate it from the spam record.
        incident = Incident(
            reporter_id=spam.reporter_id,
            image_url=restored_url,
            ai_description=spam.ai_description,
            user_description=spam.user_description,
            incident_type=spam.incident_type,
            severity_level=SeverityLevel.medium,
            latitude=spam.latitude,
            longitude=spam.longitude,
            status=IncidentStatus.verified,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        db.add(IncidentImage(incident_id=incident.id, image_url=restored_url, image_order=0))
        db.commit()

    incident = db.scalar(
        select(Incident)
        .options(selectinload(Incident.reporter))
        .where(Incident.id == incident.id)
    )

    # Tell the reporter their report was accepted after a second look.
    if incident.reporter_id:
        create_notification(
            db,
            user_id=incident.reporter_id,
            title="Your report was accepted",
            message="After review, your report was confirmed as a real incident and is now being handled.",
            type="report_approved",
            related_incident_id=incident.id,
        )
    notify_officers_new_incident(db, incident)

    emit_incident_event(incident, "incident.analyzed")
    emit_incident_event(incident, "incident.created")

    db.delete(spam)
    db.commit()

    incident = db.scalar(
        select(Incident)
        .options(selectinload(Incident.reporter))
        .where(Incident.id == incident.id)
    )
    return incident


@router.delete("/{spam_id}", response_model=MessageResponse)
def delete_spam(
    spam_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Permanently delete a spam report and its quarantined image (admin only)."""
    spam = db.get(SpamReport, spam_id)
    if not spam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spam report not found")
    delete_upload_file(spam.image_url)
    db.delete(spam)
    db.commit()
    return MessageResponse(message="Spam report deleted")
