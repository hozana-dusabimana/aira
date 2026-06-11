from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import require_admin, require_officer
from app.core.security import hash_password
from app.database import get_db
from app.models.incident import Incident
from app.models.officer import Officer
from app.models.station import Station
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.incident import IncidentOut
from app.schemas.officer import OfficerCreate, OfficerOut, OfficerUpdate, StationOut

router = APIRouter()


def _serialize(officer: Officer) -> OfficerOut:
    """Merge the officer row with its linked user account for the dashboard."""
    user = officer.user
    return OfficerOut(
        id=officer.id,
        user_id=officer.user_id,
        badge_number=officer.badge_number,
        station_id=officer.station_id,
        rank=officer.rank,
        department=officer.department,
        full_name=user.full_name if user else None,
        email=user.email if user else None,
        phone=user.phone if user else None,
        is_active=user.is_active if user else True,
        created_at=officer.created_at,
    )


@router.get("/", response_model=list[OfficerOut])
def list_officers(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> list[OfficerOut]:
    officers = db.scalars(
        select(Officer).options(selectinload(Officer.user)).order_by(Officer.id)
    ).all()
    return [_serialize(o) for o in officers]


@router.post("/", response_model=OfficerOut, status_code=status.HTTP_201_CREATED)
def create_officer(
    payload: OfficerCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> Officer:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    if db.query(Officer).filter(Officer.badge_number == payload.badge_number).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Badge already exists")

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.officer,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    officer = Officer(
        user_id=user.id,
        badge_number=payload.badge_number,
        station_id=payload.station_id,
        rank=payload.rank,
        department=payload.department,
    )
    db.add(officer)
    db.commit()
    db.refresh(officer)
    return _serialize(officer)


@router.put("/{officer_id}", response_model=OfficerOut)
def update_officer(
    officer_id: int,
    payload: OfficerUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> OfficerOut:
    officer = db.get(Officer, officer_id)
    if not officer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer not found")
    user = db.get(User, officer.user_id)

    if payload.badge_number is not None and payload.badge_number != officer.badge_number:
        clash = db.query(Officer).filter(
            Officer.badge_number == payload.badge_number, Officer.id != officer.id
        ).first()
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Badge already exists")
        officer.badge_number = payload.badge_number

    if payload.station_id is not None:
        officer.station_id = payload.station_id
    if payload.rank is not None:
        officer.rank = payload.rank
    if payload.department is not None:
        officer.department = payload.department

    if user:
        if payload.email is not None and payload.email.lower() != (user.email or ""):
            clash = db.query(User).filter(
                User.email == payload.email.lower(), User.id != user.id
            ).first()
            if clash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
            user.email = payload.email.lower()
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.phone is not None:
            user.phone = payload.phone
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.password:
            user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(officer)
    return _serialize(officer)


@router.delete("/{officer_id}", response_model=MessageResponse)
def delete_officer(
    officer_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    officer = db.get(Officer, officer_id)
    if not officer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer not found")
    user = db.get(User, officer.user_id)
    # Deleting the officer nulls out any incidents assigned to them
    # (incidents.assigned_officer_id is ON DELETE SET NULL). Removing the linked
    # user account too fully revokes the officer's login.
    db.delete(officer)
    if user:
        db.delete(user)
    db.commit()
    return MessageResponse(message="Officer deleted")


@router.get("/stations", response_model=list[StationOut])
def list_stations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> list[Station]:
    return list(db.scalars(select(Station).order_by(Station.name)).all())


@router.get("/{officer_id}/incidents", response_model=list[IncidentOut])
def officer_incidents(
    officer_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> list[Incident]:
    stmt = (
        select(Incident)
        .where(Incident.assigned_officer_id == officer_id)
        .order_by(Incident.created_at.desc())
    )
    return list(db.scalars(stmt).all())
