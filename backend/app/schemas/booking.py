from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BookingCreate(BaseModel):
    charger_id: str = Field(min_length=1, max_length=50)
    charger_name: str = Field(min_length=1)
    user_email: Optional[str] = None
    vehicle_registration: Optional[str] = None
    vehicle_connector_type: Optional[str] = None
    slot_start: datetime
    slot_end: datetime

    @model_validator(mode="after")
    def validate_slot(self):
        if self.slot_end <= self.slot_start:
            raise ValueError("slot_end must be after slot_start")
        return self


class BookingOut(BaseModel):
    id: UUID
    charger_id: str
    charger_name: str
    user_email: Optional[str] = None
    vehicle_registration: Optional[str] = None
    vehicle_connector_type: Optional[str] = None
    slot_start: datetime
    slot_end: datetime
    status: str
    created_at: datetime


class BookingCancelOut(BaseModel):
    id: UUID
    status: str