from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str | None = None
    type: str
    related_incident_id: int | None = None
    is_read: bool
    created_at: datetime


class DeviceTokenCreate(BaseModel):
    token: str
    platform: str
