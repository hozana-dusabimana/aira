from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import require_admin, require_officer
from app.core.security import hash_password
from app.database import get_db
from app.models.incident import Incident
from app.models.officer import Officer
from app.models.station import Station
from app.models.user import User, UserRole
from app.schemas.incident import IncidentOut
from app.schemas.officer import OfficerCreate, OfficerOut, StationOut

router = APIRouter()


@router.get("/", response_model=list[OfficerOut])
def list_officers(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> list[Officer]:
    return list(db.scalars(select(Officer).order_by(Officer.id)).all())


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
    return officer


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
