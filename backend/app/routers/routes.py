from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from app.schemas.trip import (
    ChargerStop,
    RouteRequest,
    RouteResponse,
)
from app.services.intelligence_adapter import (
    build_intelligent_recommendations,
)
from app.services.osrm_service import OSRMService


router = APIRouter(
    prefix="/routes",
    tags=["routes"],
)

osrm_service = OSRMService()

USER_TIMEZONE = ZoneInfo("Asia/Kolkata")


def normalize_departure_time(
    departure_time: datetime | None,
) -> datetime | None:
    """
    Normalize user-provided departure time to Asia/Kolkata.
    """

    if departure_time is None:
        return None

    if departure_time.tzinfo is None:
        return departure_time.replace(
            tzinfo=USER_TIMEZONE
        )

    return departure_time.astimezone(
        USER_TIMEZONE
    )


@router.post(
    "/plan",
    response_model=RouteResponse,
)
async def plan_route(
    payload: RouteRequest,
):
    """
    Plan a ChargeSure route and expose the complete
    intelligence result to the frontend.
    """

    # --------------------------------------------------
    # Departure time
    # --------------------------------------------------

    departure_time = (
        normalize_departure_time(
            payload.departure_time
        )
    )

    if departure_time is not None:
        now_ist = datetime.now(
            USER_TIMEZONE
        )

        if departure_time < now_ist:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Scheduled departure time "
                    "cannot be in the past."
                ),
            )

    # --------------------------------------------------
    # OSRM route
    # --------------------------------------------------

    route = await osrm_service.get_route(
        payload.origin_lat,
        payload.origin_lng,
        payload.destination_lat,
        payload.destination_lng,
    )

    # --------------------------------------------------
    # ChargeSure intelligence
    # --------------------------------------------------

    intelligence = (
        build_intelligent_recommendations(
            route=route,
            vehicle_class=payload.vehicle_class,
            vehicle_range_km=(
                payload.vehicle_range_km
            ),
            current_charge_pct=(
                payload.current_charge_pct
            ),
            vehicle_connector_type=(
                payload.vehicle_connector_type
            ),
            departure_time=departure_time,
            top_n=3,
        )
    )

    # --------------------------------------------------
    # Build charger response
    # --------------------------------------------------

    suggested_stops = []

    for result in intelligence[
        "recommendations"
    ]:

        charger_id = str(
            result["charger_id"]
        )

        reliability_score = float(
            result.get(
                "reliability_score",
                0.0,
            )
            or 0.0
        )

        confidence_band = (
            result.get(
                "confidence_band"
            )
            or result.get(
                "reliability_confidence"
            )
            or "Medium"
        )

        reliability_confidence = (
            result.get(
                "reliability_confidence"
            )
            or confidence_band
        )

        connector_compatible = bool(
            result.get(
                "connector_compatible",
                True,
            )
        )

        connector_status = (
            result.get(
                "connector_status"
            )
            or (
                "Compatible"
                if connector_compatible
                else "Not compatible"
            )
        )

        suggested_stops.append(
            ChargerStop(
                charger_id=charger_id,

                name=result["name"],

                latitude=float(
                    result["latitude"]
                ),

                longitude=float(
                    result["longitude"]
                ),

                distance_from_origin_km=float(
                    result.get(
                        "required_distance_km",
                        result.get(
                            "distance_from_origin_km",
                            0.0,
                        ),
                    )
                    or 0.0
                ),

                reliability_score=(
                    reliability_score
                ),

                confidence_band=str(
                    confidence_band
                ),

                reliability_confidence=str(
                    reliability_confidence
                ),

                connector_compatible=(
                    connector_compatible
                ),

                connector_status=str(
                    connector_status
                ),

                estimated_arrival=(
                    result.get(
                        "estimated_arrival"
                    )
                ),

                recommended_slot_start=(
                    result.get(
                        "recommended_slot_start"
                    )
                ),

                recommended_slot_end=(
                    result.get(
                        "recommended_slot_end"
                    )
                ),

                is_grid_aware_recommended=bool(
                    result.get(
                        "is_grid_aware_recommended",
                        False,
                    )
                ),

                recommendation_rank=(
                    result.get(
                        "recommendation_rank"
                    )
                ),

                recommendation_label=(
                    result.get(
                        "recommendation_label"
                    )
                ),

                why_recommended=(
                    result.get(
                        "why_recommended"
                    )
                ),
            )
        )

    # --------------------------------------------------
    # Complete route response
    # --------------------------------------------------

    return RouteResponse(
        trip_id=uuid4(),

        distance_km=float(
            route["distance_km"]
        ),

        duration_minutes=float(
            route["duration_minutes"]
        ),

        safe_range_km=float(
            intelligence.get(
                "safe_range_km",
                0.0,
            )
            or 0.0
        ),

        candidate_count=int(
            intelligence.get(
                "candidate_count",
                0,
            )
            or 0
        ),

        safe_candidate_count=int(
            intelligence.get(
                "safe_candidate_count",
                0,
            )
            or 0
        ),

        departure_time=(
            intelligence.get(
                "departure_time"
            )
            or departure_time
        ),

        geometry=route["geometry"],

        suggested_stops=suggested_stops,
    )