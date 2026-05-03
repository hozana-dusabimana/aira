from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.realtime import broadcaster
from app.services.push_service import send_push_to_user

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str | None = None,
    type: str = "info",
    related_incident_id: int | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_incident_id=related_incident_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    logger.info("Notification[%s] -> user %s: %s", type, user_id, title)

    payload = {
        "id": notif.id,
        "title": title,
        "message": message,
        "type": type,
        "related_incident_id": related_incident_id,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
    }
    broadcaster.publish(broadcaster.user_topic(user_id), "notification", payload)

    # Best-effort push delivery (FCM). Never raises — failures are logged.
    try:
        send_push_to_user(db, user_id=user_id, title=title,
                          body=message or "", data={"type": type,
                                                    "incident_id": str(related_incident_id or "")})
    except Exception:  # noqa: BLE001
        logger.exception("Push delivery failed for user %s", user_id)

    return notif
