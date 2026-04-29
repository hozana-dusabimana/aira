from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_user
from app.database import get_db
from app.models.device_token import DeviceToken, Platform
from app.models.notification import Notification
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.notification import DeviceTokenCreate, NotificationOut

router = APIRouter()


@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Notification:
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/register-device", response_model=MessageResponse)
def register_device(
    payload: DeviceTokenCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        platform = Platform(payload.platform)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid platform")

    existing = db.query(DeviceToken).filter(DeviceToken.token == payload.token).first()
    if existing:
        existing.user_id = current_user.id
        existing.platform = platform
    else:
        db.add(DeviceToken(user_id=current_user.id, token=payload.token, platform=platform))
    db.commit()
    return MessageResponse(message="Device registered")
