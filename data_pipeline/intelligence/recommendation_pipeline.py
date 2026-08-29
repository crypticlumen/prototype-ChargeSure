from data_pipeline.intelligence.candidate_repository import (
    get_route_candidates,
)

from data_pipeline.intelligence.recommendation import (
    ChargerCandidate,
    recommend,
)

from data_pipeline.intelligence.reliability import (
    get_reliability_score,
)

from data_pipeline.routing.osrm_access import (
    get_road_access_distance,
)


# Current demo vehicle.
# We will make these user inputs later.

BATTERY_PERCENT = 42.0
BATTERY_CAPACITY_KWH = 3.2
EFFICIENCY_WH_PER_KM = 45.0

SAFETY_RESERVE_PERCENT = 20.0


def calculate_safe_range() -> float:

    available_energy_kwh = (
        BATTERY_CAPACITY_KWH
        * BATTERY_PERCENT
        / 100
    )

    available_energy_wh = (
        available_energy_kwh * 1000
    )

    estimated_range_km = (
        available_energy_wh
        / EFFICIENCY_WH_PER_KM
    )

    safe_range_km = (
        estimated_range_km
        * (1 - SAFETY_RESERVE_PERCENT / 100)
    )

    return safe_range_km


def main():

    safe_range_km = calculate_safe_range()

    candidates = get_route_candidates()

    recommendation_candidates = []

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

        required_distance_km = (
            candidate["route_progress_km"]
            + road_access_km
        )

        range_safe = (
            required_distance_km <= safe_range_km
        )

        recommendation_candidates.append(
            ChargerCandidate(
                charger_id=candidate["charger_id"],
                name=candidate["name"],
                city=candidate["city"],
                state=candidate["state"],
                route_progress_km=(
                    candidate["route_progress_km"]
                ),
                road_access_km=road_access_km,
                range_safe=range_safe,
                reliability_score=(
                    get_reliability_score(
                        candidate["charger_id"]
                    )
                ),
                availability_score=75.0,
                trust_score=70.0,
            )
        )

    recommendations = recommend(
        recommendation_candidates,
        top_n=3,
    )

    print()
    print("CHARGESURE DATABASE-DRIVEN RECOMMENDATION")
    print("=" * 110)

    print(
        f"Battery: {BATTERY_PERCENT:.0f}%"
    )

    print(
        f"Safe range: {safe_range_km:.2f} km"
    )

    print(
        f"Route candidates: {len(candidates)}"
    )

    print(
        f"Safe candidates: "
        f"{sum(c.range_safe for c in recommendation_candidates)}"
    )

    print("=" * 110)

    if not recommendations:
        print(
            "No reachable charger "
            "was found."
        )
        return

    for result in recommendations:

        print()
        print(
            f"#{result['rank']} "
            f"{result['name']}"
        )

        print(
            f"   ID: "
            f"{result['charger_id']}"
        )

        print(
            f"   Score: "
            f"{result['final_score']}"
        )

        print(
            f"   Reliability: "
            f"{result['reliability_score']}"
        )

        print(
            f"   Route progress: "
            f"{result['route_progress_km']:.2f} km"
        )

        print(
            f"   Road access: "
            f"{result['road_access_km']:.2f} km"
        )

        print(
            f"   Range safe: "
            f"{result['range_safe']}"
        )

        print("   Why:")

        for reason in result["reasons"]:
            print(
                f"     ✓ {reason}"
            )


if __name__ == "__main__":
    main()