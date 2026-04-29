import logging

from app.database import session_scope
from app.services.ai_service import analyze_incident_sync
from app.services.notification_service import create_notification
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="aira.analyze_incident", bind=True, max_retries=3)
def analyze_incident_task(self, incident_id: int) -> int | None:
    """Background AI analysis of a submitted incident."""
    try:
        with session_scope() as db:
            analysis = analyze_incident_sync(db, incident_id)
            if analysis is None:
                logger.warning("AI analysis returned None for incident %s", incident_id)
                return None

            # Notify the reporter
            from app.models.incident import Incident
            incident = db.get(Incident, incident_id)
            if incident:
                create_notification(
                    db,
                    user_id=incident.reporter_id,
                    title="Your report has been analyzed",
                    message=(incident.ai_description or "")[:500],
                    type="incident_analyzed",
                    related_incident_id=incident.id,
                )
            return analysis.id
    except Exception as exc:
        logger.exception("AI task failed for incident %s", incident_id)
        raise self.retry(exc=exc, countdown=10)
