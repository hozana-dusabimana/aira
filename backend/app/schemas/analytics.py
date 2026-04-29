from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    total_reports: int
    pending: int
    resolved: int
    in_progress: int
    average_response_minutes: float | None = None


class CountByLabel(BaseModel):
    label: str
    count: int


class TimelinePoint(BaseModel):
    date: str
    count: int


class GeoPoint(BaseModel):
    latitude: float
    longitude: float
    count: int


class ResponseMetrics(BaseModel):
    average_response_minutes: float | None
    median_response_minutes: float | None
    resolved_last_24h: int
    resolved_last_7d: int
