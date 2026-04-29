from __future__ import annotations

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
from app.services.ai_service import analyze_incident_sync
from app.services.file_service import save_upload
from app.services.notification_service import create_notification

router = APIRouter()


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
def submit_incident(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    image: UploadFile = File(...),
    user_description: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    incident_type: str | None = Form(None),
    severity_level: str = Form("medium"),
    run_ai: bool = Form(True),
) -> Incident:
    """Submit a new incident report. AI analysis runs synchronously by default
    (so the API response already contains the description). Set ``run_ai=false``
    to defer to a background worker."""
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
        analyze_incident_sync(db, incident.id)
        db.refresh(incident)
    else:
        # Dispatch async to the Celery worker. If the broker is unreachable
        # (e.g. dev box without Redis), fall back to a sync run so the
        # incident still gets processed.
        try:
            from app.tasks.ai_tasks import analyze_incident_task
            analyze_incident_task.delay(incident.id)
        except Exception:  # noqa: BLE001
            analyze_incident_sync(db, incident.id)
            db.refresh(incident)

    # Eager-load relationships for the response
    incident = db.scalar(
        select(Incident)
        .options(selectinload(Incident.images), selectinload(Incident.ai_analysis))
        .where(Incident.id == incident.id)
    )
    return incident


@router.get("/", response_model=list[IncidentOut])
def list_incidents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    incident_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    if current_user.role == UserRole.citizen:
        stmt = stmt.where(Incident.reporter_id == current_user.id)
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
        .options(selectinload(Incident.images), selectinload(Incident.ai_analysis))
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

    # Notify reporter
    create_notification(
        db,
        user_id=incident.reporter_id,
        title=f"Report status updated: {payload.status.value}",
        message=payload.note,
        type="status_update",
        related_incident_id=incident.id,
    )
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
