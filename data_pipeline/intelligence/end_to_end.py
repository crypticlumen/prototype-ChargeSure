import argparse

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


# =========================================================
# Vehicle configuration
# =========================================================

BATTERY_PERCENT = 42.0
BATTERY_CAPACITY_KWH = 3.2
EFFICIENCY_WH_PER_KM = 45.0
SAFETY_RESERVE_PERCENT = 20.0

DEFAULT_CONNECTOR_TYPE = "CCS"


# =========================================================
# Command-line arguments
# =========================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="ChargeSure end-to-end intelligence"
    )

    parser.add_argument(
        "--connector",
        default=DEFAULT_CONNECTOR_TYPE,
        help=(
            "Vehicle connector type "
            "(example: CCS, Type 2, CHAdeMO)"
        ),
    )

    return parser.parse_args()


# =========================================================
# Main pipeline
# =========================================================

def main():

    args = parse_args()

    vehicle_connector_type = (
        args.connector.strip()
    )

    if not vehicle_connector_type:
        raise ValueError(
            "Vehicle connector type cannot be empty."
        )

    # -----------------------------------------------------
    # Calculate vehicle safe range
    # -----------------------------------------------------

    safe_range_km = calculate_safe_range_km(
        battery_percent=BATTERY_PERCENT,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        efficiency_wh_per_km=EFFICIENCY_WH_PER_KM,
        safety_reserve_percent=SAFETY_RESERVE_PERCENT,
    )

    # -----------------------------------------------------
    # Load and enrich route candidates
    # -----------------------------------------------------

    enriched = enrich_candidates(
        vehicle_connector_type
    )

    candidates = enriched

    # -----------------------------------------------------
    # Evaluate range safety
    # -----------------------------------------------------

    evaluated = evaluate_candidates(
        enriched,
        safe_range_km,
    )

    # -----------------------------------------------------
    # Build recommendation objects
    # -----------------------------------------------------

    recommendation_candidates = []

    for candidate in evaluated:

        connector_status = candidate.get(
            "connector_compatibility",
            "UNKNOWN",
        )

        recommendation_candidate = (
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

                reliability_score=(
                    get_reliability_score(
                        candidate[
                            "charger_id"
                        ]
                    )
                ),

                # Temporary prototype values.
                availability_score=75.0,

                # Temporary prototype values.
                trust_score=70.0,

                connector_compatibility=(
                    connector_status
                ),
            )
        )

        recommendation_candidates.append(
            recommendation_candidate
        )

    # -----------------------------------------------------
    # Generate recommendations
    # -----------------------------------------------------

    recommendations = recommend(
        recommendation_candidates,
        top_n=3,
    )

    # -----------------------------------------------------
    # Calculate summary statistics
    # -----------------------------------------------------

    safe_count = sum(
        1
        for item in evaluated
        if item.get(
            "range_safe",
            False,
        )
    )

    compatible_count = sum(
        1
        for item in evaluated
        if item.get(
            "connector_compatibility",
            "UNKNOWN",
        ) == "COMPATIBLE"
    )

    unknown_count = sum(
        1
        for item in evaluated
        if item.get(
            "connector_compatibility",
            "UNKNOWN",
        ) == "UNKNOWN"
    )

    incompatible_count = sum(
        1
        for item in evaluated
        if item.get(
            "connector_compatibility",
            "UNKNOWN",
        ) == "INCOMPATIBLE"
    )

    # -----------------------------------------------------
    # Display summary
    # -----------------------------------------------------

    print()
    print(
        "CHARGESURE END-TO-END INTELLIGENCE"
    )

    print(
        "=" * 110
    )

    print(
        f"Vehicle connector: "
        f"{vehicle_connector_type}"
    )

    print(
        f"Battery: "
        f"{BATTERY_PERCENT:.0f}%"
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
        f"{safe_count}"
    )

    print(
        f"Compatible connectors: "
        f"{compatible_count}"
    )

    print(
        f"Unknown connectors: "
        f"{unknown_count}"
    )

    print(
        f"Incompatible connectors: "
        f"{incompatible_count}"
    )

    print(
        "=" * 110
    )

    # -----------------------------------------------------
    # No recommendations
    # -----------------------------------------------------

    if not recommendations:

        print(
            "No safe compatible charger found."
        )

        return

    # -----------------------------------------------------
    # Display recommendations
    # -----------------------------------------------------

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

        print(
            f"   Connector: "
            f"{result['connector_compatibility']}"
        )

        print(
            "   Why:"
        )

        for reason in result[
            "reasons"
        ]:

            print(
                f"     ✓ {reason}"
            )


if __name__ == "__main__":
    main()