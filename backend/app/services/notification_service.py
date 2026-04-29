from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.notification import Notification

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
    # In production this would also dispatch FCM/APNs/web-socket events.
    logger.info("Notification[%s] -> user %s: %s", type, user_id, title)
    return notif
