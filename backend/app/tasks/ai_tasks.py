import logging

from app.database import session_scope
from app.services.ai_service import analyze_incident_sync
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="aira.analyze_incident", bind=True, max_retries=3)
def analyze_incident_task(self, incident_id: int) -> str | None:
    """Background AI analysis of a submitted incident (legacy Celery path).

    ``analyze_incident_sync`` performs validation, persistence, reporter +
    officer notifications and realtime broadcasts itself, so this task only
    needs to invoke it and surface the outcome. Note: realtime WebSocket
    events do not reach clients from the Celery process (it holds no
    connections); the DB notifications it creates still do.
    """
    try:
        with session_scope() as db:
            outcome = analyze_incident_sync(db, incident_id)
            logger.info("AI analysis for incident %s -> %s", incident_id, outcome)
            return outcome
    except Exception as exc:
        logger.exception("AI task failed for incident %s", incident_id)
        raise self.retry(exc=exc, countdown=10)
