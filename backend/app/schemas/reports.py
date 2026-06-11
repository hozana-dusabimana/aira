from pydantic import BaseModel

from app.schemas.analytics import CountByLabel, TimelinePoint


class ReportRow(BaseModel):
    """A single incident as it appears in a generated report table."""

    id: int
    created_at: str
    incident_type: str | None
    severity: str
    status: str
    resolved_at: str | None = None
    response_minutes: float | None = None
    location: str | None = None
    reporter: str | None = None


class ReportSummary(BaseModel):
    """A self-contained, exportable incident report over a date range."""

    title: str
    generated_at: str
    start_date: str
    end_date: str
    status_filter: str | None = None

    total: int
    pending: int
    in_progress: int
    resolved: int
    rejected: int
    resolution_rate: float
    average_response_minutes: float | None = None

    by_type: list[CountByLabel]
    by_severity: list[CountByLabel]
    timeline: list[TimelinePoint]
    rows: list[ReportRow]
