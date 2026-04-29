from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_user
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.incident import Incident
from app.models.notification import Notification
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.incident import IncidentOut
from app.schemas.notification import NotificationOut
from app.schemas.user import ChangePasswordRequest, UserOut, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.national_id is not None:
        current_user.national_id = payload.national_id
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return MessageResponse(message="Password updated")


@router.get("/me/incidents", response_model=list[IncidentOut])
def my_incidents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Incident]:
    stmt = (
        select(Incident)
        .where(Incident.reporter_id == current_user.id)
        .order_by(Incident.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/me/notifications", response_model=list[NotificationOut])
def my_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return list(db.scalars(stmt).all())
