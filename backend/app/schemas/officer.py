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
