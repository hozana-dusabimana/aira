from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import get_current_user, require_admin
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.incident import Incident
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.incident import IncidentOut
from app.schemas.notification import NotificationOut
from app.schemas.user import AdminUserUpdate, ChangePasswordRequest, UserOut, UserUpdate

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
        .options(selectinload(Incident.reporter))
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


# --- Admin: citizen management -------------------------------------------


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    role: UserRole = UserRole.citizen,
) -> list[User]:
    """List user accounts of a given role (citizens by default)."""
    stmt = select(User).where(User.role == role).order_by(User.created_at.desc())
    return list(db.scalars(stmt).all())


@router.put("/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.national_id is not None:
        user.national_id = payload.national_id
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_verified is not None:
        user.is_verified = payload.is_verified
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def admin_delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    if user.role != UserRole.citizen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only citizen accounts can be deleted here; use the Officers page for officers.",
        )
    # Delete the citizen's incidents first so their children (images, AI
    # analysis, updates, messages) are removed via ORM cascade, then the user
    # (cascades notifications and device tokens).
    incidents = db.scalars(select(Incident).where(Incident.reporter_id == user.id)).all()
    for incident in incidents:
        db.delete(incident)
    db.delete(user)
    db.commit()
    return MessageResponse(message="Citizen deleted")
