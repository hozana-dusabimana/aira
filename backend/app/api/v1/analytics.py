from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.permissions import require_officer
from app.database import get_db
from app.models.incident import Incident, IncidentStatus
from app.models.user import User
from app.schemas.analytics import (
    CountByLabel,
    GeoPoint,
    OverviewMetrics,
    ResponseMetrics,
    TimelinePoint,
)

router = APIRouter()

# The reportable incident_type categories the system tracks. These are the two
# real incident classes the self-trained classifier produces (``normal``/
# ``general`` is explicitly NOT a reportable incident). ``by_type`` always
# reports every one of these — including zero-count types — so the dashboard/
# analytics charts show both categories, not just the one that has data.
CANONICAL_INCIDENT_TYPES: tuple[str, ...] = (
    "fire",
    "traffic",
)


def _avg_response_minutes(db: Session) -> float | None:
    rows = db.execute(
        select(Incident.created_at, Incident.resolved_at).where(Incident.resolved_at.is_not(None))
    ).all()
    if not rows:
        return None
    minutes = [(r.resolved_at - r.created_at).total_seconds() / 60 for r in rows]
    return round(sum(minutes) / len(minutes), 1) if minutes else None


@router.get("/overview", response_model=OverviewMetrics)
def overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> OverviewMetrics:
    total = db.scalar(select(func.count(Incident.id))) or 0
    pending = db.scalar(
        select(func.count(Incident.id)).where(Incident.status == IncidentStatus.pending)
    ) or 0
    resolved = db.scalar(
        select(func.count(Incident.id)).where(Incident.status == IncidentStatus.resolved)
    ) or 0
    in_progress = db.scalar(
        select(func.count(Incident.id)).where(Incident.status == IncidentStatus.in_progress)
    ) or 0
    return OverviewMetrics(
        total_reports=total,
        pending=pending,
        resolved=resolved,
        in_progress=in_progress,
        average_response_minutes=_avg_response_minutes(db),
    )


@router.get("/incidents-by-type", response_model=list[CountByLabel])
def by_type(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> list[CountByLabel]:
    rows = db.execute(
        select(
            func.coalesce(Incident.incident_type, "unknown").label("label"),
            func.count(Incident.id).label("count"),
        ).group_by(Incident.incident_type)
    ).all()
    counts = {r.label: r.count for r in rows}
    # Start from the canonical vocabulary (zero-filled) so every type is shown,
    # then append any extra labels that exist in the data but aren't canonical
    # (e.g. legacy or "unknown" rows) so nothing is silently dropped.
    labels = list(CANONICAL_INCIDENT_TYPES) + [
        label for label in counts if label not in CANONICAL_INCIDENT_TYPES
    ]
    return [CountByLabel(label=label, count=counts.get(label, 0)) for label in labels]


@router.get("/incidents-by-location", response_model=list[GeoPoint])
def by_location(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> list[GeoPoint]:
    rows = db.execute(
        select(
            func.round(Incident.latitude, 2).label("lat"),
            func.round(Incident.longitude, 2).label("lng"),
            func.count(Incident.id).label("count"),
        )
        .where(Incident.latitude.is_not(None))
        .where(Incident.longitude.is_not(None))
        .group_by("lat", "lng")
    ).all()
    return [GeoPoint(latitude=float(r.lat), longitude=float(r.lng), count=r.count) for r in rows]


@router.get("/incidents-timeline", response_model=list[TimelinePoint])
def timeline(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
    days: int = 30,
) -> list[TimelinePoint]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = db.execute(
        select(
            func.date(Incident.created_at).label("d"),
            func.count(Incident.id).label("count"),
        )
        .where(Incident.created_at >= since)
        .group_by("d")
        .order_by("d")
    ).all()
    return [TimelinePoint(date=str(r.d), count=r.count) for r in rows]


@router.get("/response-metrics", response_model=ResponseMetrics)
def response_metrics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
) -> ResponseMetrics:
    rows = db.execute(
        select(Incident.created_at, Incident.resolved_at).where(Incident.resolved_at.is_not(None))
    ).all()
    minutes = sorted([(r.resolved_at - r.created_at).total_seconds() / 60 for r in rows])
    avg = round(sum(minutes) / len(minutes), 1) if minutes else None
    median = minutes[len(minutes) // 2] if minutes else None
    if median is not None:
        median = round(median, 1)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last24 = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.status == IncidentStatus.resolved,
            Incident.resolved_at >= now - timedelta(hours=24),
        )
    ) or 0
    last7 = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.status == IncidentStatus.resolved,
            Incident.resolved_at >= now - timedelta(days=7),
        )
    ) or 0
    return ResponseMetrics(
        average_response_minutes=avg,
        median_response_minutes=median,
        resolved_last_24h=last24,
        resolved_last_7d=last7,
    )
