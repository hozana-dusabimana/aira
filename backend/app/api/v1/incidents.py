import logging
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.permissions import get_current_user, require_admin, require_officer
from app.database import get_db
from app.models.feedback_message import FeedbackMessage
from app.models.incident import Incident, IncidentStatus, SeverityLevel
from app.models.incident_image import IncidentImage
from app.models.incident_update import IncidentUpdate
from app.models.officer import Officer
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.incident import (
    IncidentAssign,
    IncidentDetail,
    IncidentMessageCreate,
    IncidentMessageOut,
    IncidentOut,
    IncidentStatusUpdate,
)
from app.core.rate_limit import INCIDENT_SUBMIT_LIMIT, limiter
from app.realtime import broadcaster
from app.services.ai_service import analyze_incident_sync, emit_incident_event
from app.services.file_service import save_upload
from app.services.notification_service import create_notification

router = APIRouter()

logger = logging.getLogger(__name__)

# Per-status (title, default message, notification type) used when the
# reporter is notified that an officer acted on their report.
_STATUS_NOTIFICATION: dict[IncidentStatus, tuple[str, str, str]] = {
    IncidentStatus.verified: (
        "Your report was approved",
        "An officer has reviewed and approved your report. It is now being acted on.",
        "report_approved",
    ),
    IncidentStatus.assigned: (
        "An officer is on your report",
        "Your report has been approved and assigned to an officer.",
        "report_approved",
    ),
    IncidentStatus.in_progress: (
        "Officers are responding",
        "Officers are now actively responding to your reported incident.",
        "status_update",
    ),
    IncidentStatus.resolved: (
        "Your report is resolved",
        "Your reported incident has been resolved. Thank you for reporting.",
        "report_resolved",
    ),
    IncidentStatus.rejected: (
        "Report could not be confirmed",
        "After review, your report could not be confirmed as an incident.",
        "report_rejected",
    ),
}


# --- Helpers ----------------------------------------------------------

def _user_can_see(user: User, incident: Incident) -> bool:
    if user.role in (UserRole.officer, UserRole.admin):
        return True
    return incident.reporter_id == user.id


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


# --- Endpoints --------------------------------------------------------

@router.post("/", response_model=IncidentDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit(INCIDENT_SUBMIT_LIMIT)
def submit_incident(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    user_description: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    incident_type: str | None = Form(None),
    severity_level: str = Form("medium"),
    run_ai: bool = Form(True),
) -> Incident:
    """Submit a new incident report.

    With ``run_ai=true`` (default) AI analysis runs synchronously so the HTTP
    response already contains the AI summary. With ``run_ai=false`` the report
    is created with status ``analyzing`` and the analysis runs in a background
    task; the client receives the result via realtime events / polling. The
    mobile app uses the async mode so submission is instant."""
    image_url, _ = save_upload(image)

    try:
        sev = SeverityLevel(severity_level)
    except ValueError:
        sev = SeverityLevel.medium

    incident = Incident(
        reporter_id=current_user.id,
        image_url=image_url,
        user_description=user_description,
        incident_type=incident_type,
        severity_level=sev,
        latitude=latitude,
        longitude=longitude,
        status=IncidentStatus.pending,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    # First image record
    db.add(IncidentImage(incident_id=incident.id, image_url=image_url, image_order=0))
    db.commit()

    if run_ai:
        # Synchronous: the HTTP response already carries the AI summary. Used
        # by API clients/tests that want the analysis inline. analyze_incident_sync
        # handles validation, notifications and realtime events itself.
        outcome = analyze_incident_sync(db, incident.id)
        if outcome == "rejected":
            # Don't persist a non-incident report (officers were not notified).
            db.delete(incident)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This photo doesn't appear to show a reportable incident. "
                    "Please capture the accident, fire or emergency scene and try again."
                ),
            )
        if outcome == "duplicate":
            # Same accident already reported nearby. The duplicate is kept in the
            # spam store (linked to the original); we don't file a second incident.
            db.delete(incident)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This accident appears to have already been reported. "
                    "Officers are aware — thank you for reporting."
                ),
            )
    else:
        # Async: return immediately with status=analyzing and run the analysis
        # in a background task *in this process* (so the in-process realtime
        # broadcaster can still push incident.analyzed / incident.rejected to
        # the reporter's WebSocket — a Celery worker could not, as it has no
        # WS connections bound). The mobile client polls / listens for the
        # result instead of blocking on the request.
        incident.status = IncidentStatus.analyzing
        db.commit()
        background_tasks.add_task(_run_async_analysis, incident.id)

    # Eager-load relationships for the response
    incident = db.scalar(
        select(Incident)
        .options(
            selectinload(Incident.images),
            selectinload(Incident.ai_analysis),
            selectinload(Incident.reporter),
        )
        .where(Incident.id == incident.id)
    )
    return incident


def _run_async_analysis(incident_id: int) -> None:
    """Background-task entrypoint: analyze a submitted incident out-of-band.

    Runs in the backend process (not Celery) so realtime events reach the
    reporter. On rejection the row is kept (status=rejected) and the reporter
    is told; on success analyze_incident_sync has already notified everyone.
    """
    from app.database import session_scope

    try:
        with session_scope() as db:
            outcome = analyze_incident_sync(db, incident_id)
            if outcome == "rejected":
                incident = db.get(Incident, incident_id)
                if incident is not None:
                    # Notify the reporter and push the realtime event, then
                    # discard the report entirely — no incident row is kept.
                    create_notification(
                        db,
                        user_id=incident.reporter_id,
                        title="Report could not be confirmed",
                        message=(
                            "After review, your photo could not be confirmed as a "
                            "reportable incident."
                        ),
                        type="report_rejected",
                        related_incident_id=None,
                    )
                    emit_incident_event(incident, "incident.rejected")
                    db.delete(incident)
                    db.commit()
            elif outcome == "duplicate":
                incident = db.get(Incident, incident_id)
                if incident is not None:
                    create_notification(
                        db,
                        user_id=incident.reporter_id,
                        title="This incident was already reported",
                        message=(
                            "Thank you! Someone already reported this incident nearby, "
                            "so officers are already aware of it."
                        ),
                        type="report_duplicate",
                        related_incident_id=incident.id,
                    )
                    emit_incident_event(incident, "incident.rejected")
    except Exception:  # noqa: BLE001
        logger.exception("Async analysis failed for incident %s", incident_id)


@router.get("/", response_model=list[IncidentOut])
def list_incidents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    incident_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    stmt = (
        select(Incident)
        .options(selectinload(Incident.reporter))
        .order_by(Incident.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if current_user.role == UserRole.citizen:
        # Reporters still see their own rejected reports in their history.
        stmt = stmt.where(Incident.reporter_id == current_user.id)
    elif status_filter is None:
        # Staff incidents view hides spam (rejected) — it lives on the Spam page.
        stmt = stmt.where(Incident.status != IncidentStatus.rejected)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if incident_type:
        stmt = stmt.where(Incident.incident_type == incident_type)
    return list(db.scalars(stmt).all())


@router.get("/nearby", response_model=list[IncidentOut])
def nearby_incidents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(default=5.0, gt=0, le=200),
) -> list[Incident]:
    # Pre-filter with bounding box for performance, then refine with haversine.
    delta = radius_km / 111.0
    stmt = (
        select(Incident)
        .options(selectinload(Incident.reporter))
        .where(Incident.latitude.is_not(None))
        .where(Incident.longitude.is_not(None))
        .where(Incident.latitude.between(lat - delta, lat + delta))
        .where(Incident.longitude.between(lng - delta, lng + delta))
    )
    if current_user.role == UserRole.citizen:
        stmt = stmt.where(Incident.reporter_id == current_user.id)
    candidates = list(db.scalars(stmt).all())
    return [
        i for i in candidates
        if i.latitude is not None
        and i.longitude is not None
        and _haversine_km(lat, lng, float(i.latitude), float(i.longitude)) <= radius_km
    ]


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Incident:
    incident = db.scalar(
        select(Incident)
        .options(
            selectinload(Incident.images),
            selectinload(Incident.ai_analysis),
            selectinload(Incident.reporter),
        )
        .where(Incident.id == incident_id)
    )
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if not _user_can_see(current_user, incident):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return incident


@router.put("/{incident_id}/status", response_model=IncidentOut)
def update_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_officer)],
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = payload.status
    if payload.status == IncidentStatus.resolved:
        incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)

    officer_pk = None
    if current_user.role == UserRole.officer:
        officer = db.scalar(select(Officer).where(Officer.user_id == current_user.id))
        if officer:
            officer_pk = officer.id

    db.add(IncidentUpdate(
        incident_id=incident.id,
        officer_id=officer_pk,
        status_change=payload.status.value,
        update_message=payload.note,
    ))
    db.commit()
    db.refresh(incident)

    # Notify reporter, with friendly per-status wording.
    title, default_msg, notif_type = _STATUS_NOTIFICATION.get(
        payload.status,
        ("Report updated", f"Your report status is now {payload.status.value}.", "status_update"),
    )
    create_notification(
        db,
        user_id=incident.reporter_id,
        title=title,
        message=payload.note or default_msg,
        type=notif_type,
        related_incident_id=incident.id,
    )
    emit_incident_event(incident, "incident.status_changed")
    return incident


@router.post("/{incident_id}/assign", response_model=IncidentOut)
def assign_incident(
    incident_id: int,
    payload: IncidentAssign,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    officer = db.get(Officer, payload.officer_id)
    if not officer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer not found")
    incident.assigned_officer_id = officer.id
    if officer.station_id:
        incident.station_id = officer.station_id
    if incident.status == IncidentStatus.pending or incident.status == IncidentStatus.verified:
        incident.status = IncidentStatus.assigned
    db.commit()
    db.refresh(incident)

    # Notify the officer
    create_notification(
        db,
        user_id=officer.user_id,
        title="A new incident has been assigned to you",
        message=incident.ai_description or incident.user_description,
        type="incident_assigned",
        related_incident_id=incident.id,
    )
    emit_incident_event(incident, "incident.assigned")
    return incident


@router.delete("/{incident_id}", response_model=MessageResponse)
def delete_incident(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    db.delete(incident)
    db.commit()
    return MessageResponse(message="Incident deleted")


@router.post("/{incident_id}/messages", response_model=IncidentMessageOut, status_code=201)
def post_message(
    incident_id: int,
    payload: IncidentMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FeedbackMessage:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if not _user_can_see(current_user, incident):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    msg = FeedbackMessage(
        incident_id=incident.id,
        sender_id=current_user.id,
        sender_role=current_user.role,
        message=payload.message,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Notify the other party
    target_user_id = (
        incident.reporter_id
        if current_user.role != UserRole.citizen
        else (incident.assigned_officer.user_id if incident.assigned_officer else None)
    )
    if target_user_id and target_user_id != current_user.id:
        create_notification(
            db,
            user_id=target_user_id,
            title="New message on your incident",
            message=payload.message[:200],
            type="message",
            related_incident_id=incident.id,
        )

    broadcaster.publish(
        broadcaster.incident_topic(incident.id),
        "incident.message",
        {
            "id": msg.id,
            "incident_id": incident.id,
            "sender_id": msg.sender_id,
            "sender_role": msg.sender_role.value if hasattr(msg.sender_role, "value") else msg.sender_role,
            "message": msg.message,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        },
    )
    return msg


@router.get("/{incident_id}/messages", response_model=list[IncidentMessageOut])
def list_messages(
    incident_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FeedbackMessage]:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if not _user_can_see(current_user, incident):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    stmt = (
        select(FeedbackMessage)
        .where(FeedbackMessage.incident_id == incident.id)
        .order_by(FeedbackMessage.created_at.asc())
    )
    return list(db.scalars(stmt).all())
