from uuid import uuid4

from fastapi import APIRouter

from app.schemas.trip import (
    RouteRequest,
    RouteResponse,
    ChargerStop,
)
from app.services.osrm_service import OSRMService
from app.services.intelligence_adapter import (
    build_intelligent_recommendations,
)

router = APIRouter(
    prefix="/routes",
    tags=["routes"],
)

osrm_service = OSRMService()


@router.post(
    "/plan",
    response_model=RouteResponse,
)
async def plan_route(
    payload: RouteRequest,
):
    route = await osrm_service.get_route(
        payload.origin_lat,
        payload.origin_lng,
        payload.destination_lat,
        payload.destination_lng,
    )

    intelligence = build_intelligent_recommendations(
        route=route,
        vehicle_class=payload.vehicle_class,
        vehicle_range_km=payload.vehicle_range_km,
        current_charge_pct=payload.current_charge_pct,
        vehicle_connector_type=(
            payload.vehicle_connector_type
        ),
        top_n=3,
    )

    suggested_stops = []

    for result in intelligence["recommendations"]:
        suggested_stops.append(
            ChargerStop(
                charger_id=str(result["charger_id"]),
                name=result["name"],
                latitude=float(result["latitude"]),
                longitude=float(result["longitude"]),
                distance_from_origin_km=float(
                    result["required_distance_km"]
                ),
                reliability_score=float(
                    result["reliability_score"]
                ),
                confidence_band="medium",
                recommended_slot_start=None,
                recommended_slot_end=None,
                is_grid_aware_recommended=False,
            )
        )

    return RouteResponse(
        trip_id=uuid4(),
        distance_km=route["distance_km"],
        duration_minutes=route["duration_minutes"],
        geometry=route["geometry"],
        suggested_stops=suggested_stops,
    )