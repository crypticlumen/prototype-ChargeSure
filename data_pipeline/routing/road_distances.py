from route import get_road_distances
from route_candidates import get_route_candidates


# Ahmedabad
ORIGIN_LAT = 23.0225
ORIGIN_LON = 72.5714


def main():

    candidates = get_route_candidates()

    destinations = [
        {
            "id": candidate["charger_id"],
            "lat": candidate["latitude"],
            "lon": candidate["longitude"],
        }
        for candidate in candidates
    ]

    road_distances = get_road_distances(
        ORIGIN_LON,
        ORIGIN_LAT,
        destinations,
    )

    candidate_map = {
        candidate["charger_id"]: candidate
        for candidate in candidates
    }

    print()
    print("ROAD DISTANCES")
    print("=" * 80)

    for result in road_distances:

        charger = candidate_map[result["id"]]

        print(
            f"{charger['charger_id']} | "
            f"{charger['name']} | "
            f"route-distance: "
            f"{charger['distance_from_route_km']:.2f} km | "
            f"road-distance-from-origin: "
            f"{result['distance_km']:.2f} km | "
            f"time: "
            f"{result['duration_minutes']:.2f} min"
        )


if __name__ == "__main__":
    main()