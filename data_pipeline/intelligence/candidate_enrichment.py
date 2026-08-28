from data_pipeline.intelligence.candidate_repository import (
    get_route_candidates,
)

from data_pipeline.routing.osrm_access import (
    get_road_access_distance,
)


def enrich_candidates() -> list[dict]:

    candidates = get_route_candidates()

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

        enriched_candidate = {
            **candidate,
            "road_access_km": road_access_km,
            "road_access_minutes": road_access_minutes,
        }

        enriched.append(
            enriched_candidate
        )

    return enriched


if __name__ == "__main__":

    candidates = enrich_candidates()

    print("ENRICHED ROUTE CANDIDATES")
    print("=" * 110)

    print(
        f"Candidates: {len(candidates)}"
    )

    print()

    for candidate in candidates:

        print(
            f"{candidate['charger_id']} | "
            f"{candidate['name']} | "
            f"progress: "
            f"{candidate['route_progress_km']:.2f} km | "
            f"from route: "
            f"{candidate['distance_from_route_km']:.2f} km | "
            f"road access: "
            f"{candidate['road_access_km']:.2f} km | "
            f"time: "
            f"{candidate['road_access_minutes']:.2f} min"
        )