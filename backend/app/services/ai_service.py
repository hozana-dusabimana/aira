from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.description_generator import generate_description
from app.ai.image_analyzer import get_analyzer
from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.incident import Incident, IncidentStatus, SeverityLevel
from app.models.user import User, UserRole
from app.realtime import broadcaster
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

# Categories that mean "the AI could not recognise a real incident". Uploads
# that classify into one of these (or have no type at all) are treated as
# non-incidents so officers are not disturbed by them.
_NON_INCIDENT_TYPES = {"", "general"}


def looks_like_incident(incident: Incident) -> bool:
    return (incident.incident_type or "").strip().lower() not in _NON_INCIDENT_TYPES


def _read_image_bytes(image_url: str | None) -> bytes | None:
    if not image_url:
        return None
    # image_url is stored as "/uploads/<file>"
    rel = image_url.lstrip("/")
    abs_path = Path(settings.UPLOAD_DIR).resolve().parent / rel
    if not abs_path.exists():
        # try direct
        abs_path = Path(settings.UPLOAD_DIR).resolve() / Path(rel).name
    if not abs_path.exists():
        logger.warning("Image not found for analysis: %s", image_url)
        return None
    return abs_path.read_bytes()


def delete_upload_file(image_url: str | None) -> None:
    """Best-effort removal of a stored upload (used when a report is rejected)."""
    if not image_url:
        return
    rel = image_url.lstrip("/")
    try:
        path = Path(settings.UPLOAD_DIR).resolve().parent / rel
        if not path.exists():
            path = Path(settings.UPLOAD_DIR).resolve() / Path(rel).name
        path.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        logger.debug("Could not delete rejected upload: %s", image_url)


def _incident_payload(incident: Incident) -> dict:
    reporter = incident.reporter
    return {
        "id": incident.id,
        "status": incident.status.value if incident.status else None,
        "incident_type": incident.incident_type,
        "severity_level": incident.severity_level.value if incident.severity_level else None,
        "ai_description": incident.ai_description,
        "user_description": incident.user_description,
        "image_url": incident.image_url,
        "latitude": float(incident.latitude) if incident.latitude is not None else None,
        "longitude": float(incident.longitude) if incident.longitude is not None else None,
        "reporter_id": incident.reporter_id,
        "reporter": (
            {"id": reporter.id, "full_name": reporter.full_name, "phone": reporter.phone}
            if reporter
            else None
        ),
        "assigned_officer_id": incident.assigned_officer_id,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
    }


def emit_incident_event(incident: Incident, event: str) -> None:
    payload = _incident_payload(incident)
    broadcaster.publish(broadcaster.staff_topic(), event, payload)
    broadcaster.publish(broadcaster.user_topic(incident.reporter_id), event, payload)
    broadcaster.publish(broadcaster.incident_topic(incident.id), event, payload)


def notify_officers_new_incident(db: Session, incident: Incident) -> None:
    """Notify every active officer that a new (verified) report has come in."""
    officer_ids = db.scalars(
        select(User.id).where(User.role == UserRole.officer, User.is_active.is_(True))
    ).all()
    summary = (
        incident.ai_description
        or incident.user_description
        or "A citizen submitted a new incident report."
    )
    for uid in officer_ids:
        create_notification(
            db,
            user_id=uid,
            title=f"New {(incident.incident_type or 'incident').replace('_', ' ')} report submitted",
            message=summary[:200],
            type="incident_reported",
            related_incident_id=incident.id,
        )


def analyze_incident_sync(db: Session, incident_id: int) -> str:
    """Run AI analysis, validate, persist, notify and broadcast.

    This is the single source of truth for both the synchronous request path
    and the background/worker path. It returns one of:

    * ``"analyzed"`` — a real incident; status set to ``verified``, the AI
      analysis persisted, the reporter + officers notified and an
      ``incident.analyzed`` / ``incident.created`` event broadcast.
    * ``"rejected"`` — the photo does not look like a reportable incident;
      status set to ``rejected`` and the stored upload deleted. The caller
      decides whether to keep the row (async) or delete it (sync 422).
    * ``"skipped"`` — the incident or its image could not be loaded.
    """
    incident = db.get(Incident, incident_id)
    if not incident:
        logger.error("Incident %s not found", incident_id)
        return "skipped"

    incident.status = IncidentStatus.analyzing
    db.commit()

    img_bytes = _read_image_bytes(incident.image_url)
    if img_bytes is None:
        incident.status = IncidentStatus.pending
        db.commit()
        return "skipped"

    analyzer = get_analyzer()
    result = analyzer.analyze(img_bytes)

    # AI summary is generated purely from the image; the citizen's own
    # description is intentionally excluded so the AI report stands as an
    # objective second opinion on the scene.
    incident.ai_description = generate_description(result)
    if not incident.incident_type:
        incident.incident_type = result.incident_type
    try:
        incident.severity_level = SeverityLevel(result.severity_level)
    except ValueError:
        pass

    # ---- Validation: reject non-incident photos ---------------------------
    if settings.INCIDENT_VALIDATION_ENABLED and not looks_like_incident(incident):
        incident.status = IncidentStatus.rejected
        db.commit()
        delete_upload_file(incident.image_url)
        logger.info("Incident %s rejected as non-incident (type=%s)",
                    incident_id, incident.incident_type)
        return "rejected"

    # ---- Accepted: persist analysis, notify and broadcast -----------------
    incident.status = IncidentStatus.verified

    analysis = AIAnalysis(
        incident_id=incident.id,
        detected_objects=result.detected_objects,
        scene_label=result.scene_label,
        caption=result.caption,
        confidence_score=result.confidence_score,
        model_version=result.model_version,
        raw_output=result.raw_output,
    )
    db.add(analysis)
    db.commit()

    # Eager-load reporter so the broadcast payload is complete.
    incident = db.scalar(select(Incident).where(Incident.id == incident.id))

    # Reporter: their report is ready.
    create_notification(
        db,
        user_id=incident.reporter_id,
        title="Your report has been analyzed",
        message=(incident.ai_description or "")[:500],
        type="incident_analyzed",
        related_incident_id=incident.id,
    )
    # Officers: a new report needs attention.
    notify_officers_new_incident(db, incident)

    # incident.analyzed updates any open detail/list view; incident.created
    # makes the dashboard add the card (it only adds on "created").
    emit_incident_event(incident, "incident.analyzed")
    emit_incident_event(incident, "incident.created")

    return "analyzed"
