"""FCM push notification delivery.

Uses FCM HTTP v1 legacy endpoint with the server key from config. Disabled
unless ``FCM_SERVER_KEY`` is configured. Failures never raise — push is a
best-effort enhancement on top of the in-app notification stream.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.device_token import DeviceToken

logger = logging.getLogger(__name__)

_FCM_URL = "https://fcm.googleapis.com/fcm/send"


def send_push_to_user(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send a push to every active device registered for this user.
    Returns the number of devices that received a successful response."""
    if not settings.FCM_SERVER_KEY:
        logger.debug("FCM disabled (no server key); skipping push for user %s", user_id)
        return 0

    tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user_id)
        .all()
    )
    if not tokens:
        return 0

    headers = {
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
        "Content-Type": "application/json",
    }
    delivered = 0
    with httpx.Client(timeout=5.0) as client:
        for tok in tokens:
            payload = {
                "to": tok.token,
                "notification": {"title": title, "body": body},
                "data": data or {},
                "priority": "high",
            }
            try:
                r = client.post(_FCM_URL, headers=headers, json=payload)
                if r.status_code == 200:
                    delivered += 1
                else:
                    logger.warning("FCM non-200 (%s): %s", r.status_code, r.text[:200])
            except httpx.HTTPError as exc:
                logger.warning("FCM request failed for device %s: %s", tok.id, exc)
    return delivered
