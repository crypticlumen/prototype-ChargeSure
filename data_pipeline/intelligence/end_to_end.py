from data_pipeline.intelligence.candidate_repository import (
    get_route_candidates,
)

from data_pipeline.intelligence.candidate_enrichment import (
    enrich_candidates,
)

from data_pipeline.intelligence.range_evaluator import (
    calculate_safe_range_km,
    evaluate_candidates,
)

from data_pipeline.intelligence.recommendation import (
    ChargerCandidate,
    recommend,
)

from data_pipeline.intelligence.reliability import (
    get_reliability_score,
)


BATTERY_PERCENT = 42.0
BATTERY_CAPACITY_KWH = 3.2
EFFICIENCY_WH_PER_KM = 45.0
SAFETY_RESERVE_PERCENT = 20.0


def main():

    safe_range_km = calculate_safe_range_km(
        battery_percent=BATTERY_PERCENT,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        efficiency_wh_per_km=EFFICIENCY_WH_PER_KM,
        safety_reserve_percent=SAFETY_RESERVE_PERCENT,
    )

    # Candidate data comes directly from PostgreSQL/PostGIS.
        # Add OSRM road-access information.
    enriched = enrich_candidates()

    candidates = enriched
    # Calculate range safety.
    evaluated = evaluate_candidates(
        enriched,
        safe_range_km,
    )

    recommendation_candidates = []

    for candidate in evaluated:

        recommendation_candidates.append(
            ChargerCandidate(
                charger_id=candidate[
                    "charger_id"
                ],

                name=candidate[
                    "name"
                ],

                city=candidate[
                    "city"
                ],

                state=candidate[
                    "state"
                ],

                route_progress_km=candidate[
                    "route_progress_km"
                ],

                road_access_km=candidate[
                    "road_access_km"
                ],

                required_distance_km=candidate[
                    "required_distance_km"
                ],

                range_safe=candidate[
                    "range_safe"
                ],

                # Temporary reliability layer.
                reliability_score=(
                    get_reliability_score(
                        candidate["charger_id"]
                    )
                ),

                # Temporary until live/status data exists.
                availability_score=75.0,

                # Temporary until crowd trust data exists.
                trust_score=70.0,

                connector_compatible=True,
            )
        )

    recommendations = recommend(
        recommendation_candidates,
        top_n=3,
    )

    print()
    print("CHARGESURE END-TO-END INTELLIGENCE")
    print("=" * 110)

    print(
        f"Battery: {BATTERY_PERCENT:.0f}%"
    )

    print(
        f"Estimated safe range: "
        f"{safe_range_km:.2f} km"
    )

    print(
        f"Route candidates: "
        f"{len(candidates)}"
    )

    print(
        f"Safe candidates: "
        f"{sum(item['range_safe'] for item in evaluated)}"
    )

    print("=" * 110)

    if not recommendations:
        print(
            "No safe compatible charger found."
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
            f"   Final score: "
            f"{result['final_score']}"
        )

        print(
            f"   Reliability: "
            f"{result['reliability_score']}"
        )

        print(
            f"   Required distance: "
            f"{result['required_distance_km']:.2f} km"
        )

        print(
            f"   Range safe: "
            f"{result['range_safe']}"
        )

        print(
            f"   Road access: "
            f"{result['road_access_km']:.2f} km"
        )

        print("   Why:")

        for reason in result["reasons"]:
            print(
                f"     ✓ {reason}"
            )


if __name__ == "__main__":
    main()