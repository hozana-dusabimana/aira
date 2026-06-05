from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.incident import ReporterOut


class SpamOut(BaseModel):
    """A quarantined (rejected) report shown on the dashboard Spam page."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int | None = None
    reporter_id: int | None = None
    image_url: str | None = None
    incident_type: str | None = None
    reason: str | None = None
    ai_caption: str | None = None
    ai_description: str | None = None
    user_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    reporter: ReporterOut | None = None
