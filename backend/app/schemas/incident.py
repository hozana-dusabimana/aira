from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.incident import IncidentStatus, SeverityLevel


class IncidentCreate(BaseModel):
    user_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    incident_type: str | None = None
    severity_level: SeverityLevel = SeverityLevel.medium


class IncidentImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    image_order: int


class AIAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    detected_objects: Any | None = None
    scene_label: str | None = None
    caption: str | None = None
    confidence_score: float | None = None
    model_version: str | None = None
    created_at: datetime


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    image_url: str | None = None
    ai_description: str | None = None
    user_description: str | None = None
    incident_type: str | None = None
    severity_level: SeverityLevel
    latitude: float | None = None
    longitude: float | None = None
    status: IncidentStatus
    assigned_officer_id: int | None = None
    station_id: int | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class IncidentDetail(IncidentOut):
    images: list[IncidentImageOut] = []
    ai_analysis: AIAnalysisOut | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    note: str | None = None


class IncidentAssign(BaseModel):
    officer_id: int


class IncidentMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class IncidentMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    sender_id: int
    sender_role: str
    message: str
    created_at: datetime
