from data_pipeline.intelligence.candidate_repository import (
    get_route_candidates,
)

from data_pipeline.routing.osrm_access import (
    get_road_access_distance,
)


def enrich_candidates(
    vehicle_connector_type: str = "CCS",
) -> list[dict]:
    """
    Get route candidates and enrich them with road-access
    information.

    The vehicle connector type is passed down to the
    candidate repository so connector compatibility is
    evaluated for the actual vehicle.
    """

    candidates = get_route_candidates(
        vehicle_connector_type
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

        enriched_candidate = {
            **candidate,

            "road_access_km": (
                road_access_km
            ),

            "road_access_minutes": (
                road_access_minutes
            ),
        }

        enriched.append(
            enriched_candidate
        )

    return enriched


if __name__ == "__main__":

    vehicle_connector_type = "CCS"

    candidates = enrich_candidates(
        vehicle_connector_type
    )

    print(
        "ENRICHED ROUTE CANDIDATES"
    )

    print(
        "=" * 140
    )

    print(
        f"Vehicle connector: "
        f"{vehicle_connector_type}"
    )

    print(
        f"Candidates: "
        f"{len(candidates)}"
    )

    print()

    for candidate in candidates:

        connector_types = ", ".join(
            candidate.get(
                "connector_types",
                [],
            )
        )

        max_power = candidate.get(
            "max_power_kw"
        )

        if max_power is None:
            max_power_text = "unknown"
        else:
            max_power_text = (
                f"{max_power:.2f}"
            )

        print(
            f"{candidate['charger_id']} | "
            f"{candidate['name']} | "
            f"progress: "
            f"{candidate['route_progress_km']:.2f} km | "
            f"from route: "
            f"{candidate['distance_from_route_km']:.2f} km | "
            f"road access: "
            f"{candidate['road_access_km']:.2f} km | "
            f"connector: "
            f"{connector_types} | "
            f"power: "
            f"{max_power_text} kW | "
            f"compatibility: "
            f"{candidate.get('connector_compatibility', 'UNKNOWN')} | "
            f"time: "
            f"{candidate['road_access_minutes']:.2f} min"
        )