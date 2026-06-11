from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    district: str | None = None
    sector: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    contact_phone: str | None = None


class OfficerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    badge_number: str
    station_id: int | None = None
    rank: str | None = None
    department: str | None = None
    # Pulled from the linked user account so the dashboard can show/edit them.
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool = True
    created_at: datetime


class OfficerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)
    badge_number: str = Field(min_length=2, max_length=50)
    station_id: int | None = None
    rank: str | None = None
    department: str | None = None


class OfficerUpdate(BaseModel):
    """All fields optional — only the provided ones are changed."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = None
    # Optional password reset; leave empty to keep the current one.
    password: str | None = Field(default=None, min_length=8, max_length=128)
    badge_number: str | None = Field(default=None, min_length=2, max_length=50)
    station_id: int | None = None
    rank: str | None = None
    department: str | None = None
    is_active: bool | None = None
