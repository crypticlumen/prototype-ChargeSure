from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float

    vehicle_class: str = "2W"
    vehicle_range_km: float = 80.0
    current_charge_pct: float = 100.0

    vehicle_connector_type: str = "CCS"

    # None = leave now.
    # When provided, this is the user's intended departure time.
    departure_time: Optional[datetime] = None

    user_id: Optional[UUID] = None

    @field_validator("vehicle_range_km")
    @classmethod
    def validate_range(
        cls,
        value: float,
    ) -> float:
        if value <= 0:
            raise ValueError(
                "vehicle_range_km must be greater than 0."
            )

        return value

    @field_validator("current_charge_pct")
    @classmethod
    def validate_charge(
        cls,
        value: float,
    ) -> float:
        if not 0 <= value <= 100:
            raise ValueError(
                "current_charge_pct must be between 0 and 100."
            )

        return value


class ChargerStop(BaseModel):
    charger_id: str
    name: str

    latitude: float
    longitude: float

    distance_from_origin_km: float

    reliability_score: float
    confidence_band: str

    # Reliability intelligence
    reliability_confidence: Optional[str] = None

    # Connector intelligence
    connector_compatible: bool = True
    connector_status: Optional[str] = None

    # Charger ETA
    estimated_arrival: Optional[datetime] = None

    # Grid / booking intelligence
    recommended_slot_start: Optional[datetime] = None
    recommended_slot_end: Optional[datetime] = None

    is_grid_aware_recommended: bool = False

    # Recommendation explanation
    recommendation_rank: Optional[int] = None
    recommendation_label: Optional[str] = None
    why_recommended: Optional[str] = None


class RouteResponse(BaseModel):
    trip_id: UUID

    distance_km: float
    duration_minutes: float

    # Safe driving range for the selected vehicle
    # at its current battery level.
    safe_range_km: float

    # Number of candidates considered by the
    # intelligent recommendation engine.
    candidate_count: Optional[int] = None

    # Number of candidates that passed the
    # range-safety evaluation.
    safe_candidate_count: Optional[int] = None

    # Actual departure used for the calculation.
    departure_time: Optional[datetime] = None

    geometry: dict

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