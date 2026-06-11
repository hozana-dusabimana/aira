from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import require_officer
from app.database import get_db
from app.models.incident import Incident, IncidentStatus
from app.models.user import User
from app.schemas.analytics import CountByLabel, TimelinePoint
from app.schemas.reports import ReportRow, ReportSummary

router = APIRouter()


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=f"Invalid date: {value!r}") from exc


def _response_minutes(inc: Incident) -> float | None:
    if inc.resolved_at is None:
        return None
    return round((inc.resolved_at - inc.created_at).total_seconds() / 60, 1)


@router.get("/summary", response_model=ReportSummary)
def summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_officer)],
    start_date: str | None = None,
    end_date: str | None = None,
    status: IncidentStatus | None = Query(default=None),
) -> ReportSummary:
    """Generate a custom incident report over a date range and optional status.

    Officers and admins build presets ("incidents this week", "resolved
    incidents", custom range) on the client; this endpoint stays a plain
    ``created_at`` range + status filter so the result is predictable and the
    same shape regardless of preset.
    """
    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
    end = _parse_date(end_date, default=today)
    start = _parse_date(start_date, default=end - timedelta(days=7))
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    stmt = (
        select(Incident)
        .options(selectinload(Incident.reporter))
        .where(Incident.created_at >= start_dt, Incident.created_at <= end_dt)
        .order_by(Incident.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    incidents = list(db.scalars(stmt).all())

    total = len(incidents)
    status_counts: Counter[str] = Counter(inc.status.value for inc in incidents)
    resolved = status_counts.get(IncidentStatus.resolved.value, 0)

    response_times = [m for inc in incidents if (m := _response_minutes(inc)) is not None]
    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else None

    type_counts: Counter[str] = Counter(inc.incident_type or "unknown" for inc in incidents)
    severity_counts: Counter[str] = Counter(inc.severity_level.value for inc in incidents)

    day_counts: Counter[str] = Counter(str(inc.created_at.date()) for inc in incidents)
    timeline = [
        TimelinePoint(date=str(start + timedelta(days=i)), count=day_counts.get(str(start + timedelta(days=i)), 0))
        for i in range((end - start).days + 1)
    ]

    rows = [
        ReportRow(
            id=inc.id,
            created_at=inc.created_at.isoformat(),
            incident_type=inc.incident_type,
            severity=inc.severity_level.value,
            status=inc.status.value,
            resolved_at=inc.resolved_at.isoformat() if inc.resolved_at else None,
            response_minutes=_response_minutes(inc),
            location=(
                f"{float(inc.latitude):.4f}, {float(inc.longitude):.4f}"
                if inc.latitude is not None and inc.longitude is not None
                else None
            ),
            reporter=inc.reporter.full_name if inc.reporter else None,
        )
        for inc in incidents
    ]

    return ReportSummary(
        title=f"Incident Report · {start.isoformat()} to {end.isoformat()}",
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        status_filter=status.value if status is not None else None,
        total=total,
        pending=status_counts.get(IncidentStatus.pending.value, 0),
        in_progress=status_counts.get(IncidentStatus.in_progress.value, 0),
        resolved=resolved,
        rejected=status_counts.get(IncidentStatus.rejected.value, 0),
        resolution_rate=round(resolved / total * 100, 1) if total else 0.0,
        average_response_minutes=avg_response,
        by_type=[CountByLabel(label=k, count=v) for k, v in sorted(type_counts.items())],
        by_severity=[CountByLabel(label=k, count=v) for k, v in sorted(severity_counts.items())],
        timeline=timeline,
        rows=rows,
    )
