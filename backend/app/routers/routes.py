from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point

from app.database import get_db
from app.models import Trip
from app.schemas.trip import RouteRequest, RouteResponse, ChargerStop
from app.services.osrm_service import OSRMService
from app.services.reliability_engine import reliability_engine
from app.services.grid_slot_recommender import grid_slot_recommender
from app.utils.geo import find_chargers_along_route, charger_lat_lng

router = APIRouter(prefix="/routes", tags=["routes"])
osrm_service = OSRMService()

MIN_RELIABILITY_SCORE_TO_SUGGEST = 55.0  # below this, don't recommend the stop at all


@router.post("/plan", response_model=RouteResponse)
async def plan_route(payload: RouteRequest, db: Session = Depends(get_db)):
    """
    The core 'Route, Trust, Book' flow from the pitch: computes the base route, finds
    chargers along the corridor, scores each for reliability, and attaches a grid-aware
    off-peak slot recommendation to every suggested stop.
    """
    route = await osrm_service.get_route(
        payload.origin_lat, payload.origin_lng, payload.destination_lat, payload.destination_lng
    )

    safe_range_km = osrm_service.safe_range_km(
        payload.vehicle_class, payload.vehicle_range_km, payload.current_charge_pct
    )

    candidates = []
    if route["distance_km"] > safe_range_km:
        candidates = find_chargers_along_route(
            db, route["geometry"], corridor_width_km=3.0, vehicle_class=payload.vehicle_class
        )

    suggested_stops = []
    cumulative_km_marker = safe_range_km  # naive: first stop should appear near the range limit
    for charger in candidates:
        score, confidence, _ = reliability_engine.score_charger(db, charger)
        if score < MIN_RELIABILITY_SCORE_TO_SUGGEST:
            continue

        lat, lng = charger_lat_lng(charger)
        slot_start, slot_end, is_grid_aware = grid_slot_recommender.recommend_slot(
            earliest_arrival=datetime.utcnow()  # placeholder: replace with ETA-to-stop once
            # per-leg ETAs are computed from the OSRM route annotations.
        )

        suggested_stops.append(
            ChargerStop(
                charger_id=charger.id,
                name=charger.name,
                latitude=lat,
                longitude=lng,
                distance_from_origin_km=cumulative_km_marker,  # refine with real leg distances
                reliability_score=score,
                confidence_band=confidence,
                recommended_slot_start=slot_start,
                recommended_slot_end=slot_end,
                is_grid_aware_recommended=is_grid_aware,
            )
        )

    # Highest reliability first, so the rider's top recommendation is also the safest bet.
    suggested_stops.sort(key=lambda s: s.reliability_score, reverse=True)

    trip = Trip(
        user_id=payload.user_id,
        origin=from_shape(Point(payload.origin_lng, payload.origin_lat), srid=4326),
        destination=from_shape(Point(payload.destination_lng, payload.destination_lat), srid=4326),
        vehicle_class=payload.vehicle_class,
        vehicle_range_km=payload.vehicle_range_km,
        planned_route={
            "geometry": route["geometry"],
            "suggested_stop_ids": [str(s.charger_id) for s in suggested_stops],
        },
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    return RouteResponse(
        trip_id=trip.id,
        distance_km=route["distance_km"],
        duration_minutes=route["duration_minutes"],
        geometry=route["geometry"],
        suggested_stops=suggested_stops,
    )
