from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.description_generator import generate_description
from app.ai.image_analyzer import get_analyzer
from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.incident import Incident, IncidentStatus, SeverityLevel
from app.realtime import broadcaster

logger = logging.getLogger(__name__)


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


def analyze_incident_sync(db: Session, incident_id: int) -> AIAnalysis | None:
    """Run AI analysis synchronously and persist the result."""
    incident = db.get(Incident, incident_id)
    if not incident:
        logger.error("Incident %s not found", incident_id)
        return None

    incident.status = IncidentStatus.analyzing
    db.commit()

    img_bytes = _read_image_bytes(incident.image_url)
    if img_bytes is None:
        incident.status = IncidentStatus.pending
        db.commit()
        return None

    analyzer = get_analyzer()
    result = analyzer.analyze(img_bytes)

    description = generate_description(result)
    incident.ai_description = description
    if not incident.incident_type:
        incident.incident_type = result.incident_type
    try:
        incident.severity_level = SeverityLevel(result.severity_level)
    except ValueError:
        pass
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
    db.refresh(analysis)

    event_payload = {
        "id": incident.id,
        "status": incident.status.value,
        "incident_type": incident.incident_type,
        "severity_level": incident.severity_level.value if incident.severity_level else None,
        "ai_description": incident.ai_description,
        "scene_label": result.scene_label,
        "confidence_score": result.confidence_score,
        "model_version": result.model_version,
    }
    broadcaster.publish(broadcaster.staff_topic(), "incident.analyzed", event_payload)
    broadcaster.publish(broadcaster.user_topic(incident.reporter_id), "incident.analyzed", event_payload)
    broadcaster.publish(broadcaster.incident_topic(incident.id), "incident.analyzed", event_payload)

    return analysis
