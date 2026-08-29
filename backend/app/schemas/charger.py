from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class ChargerBase(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    connector_types: List[str] = Field(default_factory=lambda: ["TYPE2"])
    supports_2w: bool = True
    supports_3w: bool = True
    supports_4w: bool = True
    max_power_kw: Optional[float] = None


class ChargerCreate(ChargerBase):
    external_id: Optional[str] = None
    cpo_id: Optional[UUID] = None


class ChargerOut(ChargerBase):
    id: UUID
    last_verified_at: Optional[datetime] = None
    is_active: bool
    reliability_score: Optional[float] = None
    confidence_band: Optional[str] = None

    class Config:
        from_attributes = True


class CrowdReportCreate(BaseModel):
    charger_id: UUID
    reported_status: str 
    latitude: float
    longitude: float
    notes: Optional[str] = None
