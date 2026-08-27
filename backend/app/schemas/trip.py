from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    vehicle_class: str = "2W"  # 2W | 3W | 4W
    vehicle_range_km: float = 80.0
    current_charge_pct: float = 100.0
    user_id: Optional[UUID] = None


class ChargerStop(BaseModel):
    charger_id: UUID
    name: str
    latitude: float
    longitude: float
    distance_from_origin_km: float
    reliability_score: float
    confidence_band: str
    recommended_slot_start: Optional[datetime] = None
    recommended_slot_end: Optional[datetime] = None
    is_grid_aware_recommended: bool = False


class RouteResponse(BaseModel):
    trip_id: UUID
    distance_km: float
    duration_minutes: float
    geometry: dict  # GeoJSON LineString from OSRM
    suggested_stops: List[ChargerStop]


class BookingCreate(BaseModel):
    user_id: UUID
    charger_id: UUID
    trip_id: Optional[UUID] = None
    slot_start: datetime
    slot_end: datetime


class BookingOut(BaseModel):
    id: UUID
    charger_id: UUID
    slot_start: datetime
    slot_end: datetime
    status: str
    beckn_transaction_id: Optional[str] = None

    class Config:
        from_attributes = True
