from data_pipeline.intelligence.candidate_repository import (
    get_route_candidates,
)

from data_pipeline.routing.osrm_access import (
    get_road_access_distance,
)


def enrich_candidates(
    route_geometry: dict,
    vehicle_connector_type: str = "CCS",
) -> list[dict]:
    """
    Enrich current-route candidates with road-access
    distance and connector compatibility.
    """

    candidates = get_route_candidates(
        route_geometry,
        vehicle_connector_type,
    )

    enriched = []

    for candidate in candidates:

        road_access_km, road_access_minutes = (
            get_road_access_distance(
                candidate["route_point_lon"],
                candidate["route_point_lat"],
                candidate["longitude"],
                candidate["latitude"],
            )
        )

        if road_access_km is None:
            continue

        enriched.append(
            {
                **candidate,
                "road_access_km": road_access_km,
                "road_access_minutes": road_access_minutes,
            }
        )

    return enriched