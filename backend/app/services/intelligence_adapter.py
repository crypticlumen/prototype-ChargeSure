from typing import Any

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
    get_reliability_details,
)


DEFAULT_CONNECTOR_TYPE = "CCS"
DEFAULT_SAFETY_RESERVE_PERCENT = 20.0

# The data pipeline's tested 2W profile.
# For the API, vehicle_range_km represents the range
# at 100% charge, so we derive an equivalent battery
# capacity from the efficiency figure.
VEHICLE_EFFICIENCY_WH_PER_KM = {
    "2W": 45.0,
    "3W": 45.0,
    "4W": 45.0,
}


def calculate_api_safe_range(
    vehicle_class: str,
    vehicle_range_km: float,
    current_charge_pct: float,
) -> float:
    if not 0 <= current_charge_pct <= 100:
        raise ValueError(
            "current_charge_pct must be between 0 and 100."
        )

    if vehicle_range_km <= 0:
        raise ValueError(
            "vehicle_range_km must be greater than 0."
        )

    efficiency = VEHICLE_EFFICIENCY_WH_PER_KM.get(
        vehicle_class,
        VEHICLE_EFFICIENCY_WH_PER_KM["2W"],
    )

    equivalent_battery_capacity_kwh = (
        vehicle_range_km * efficiency / 1000.0
    )

    return calculate_safe_range_km(
        battery_percent=current_charge_pct,
        battery_capacity_kwh=equivalent_battery_capacity_kwh,
        efficiency_wh_per_km=efficiency,
        safety_reserve_percent=DEFAULT_SAFETY_RESERVE_PERCENT,
    )


def build_intelligent_recommendations(
    route: dict[str, Any],
    vehicle_class: str,
    vehicle_range_km: float,
    current_charge_pct: float,
    vehicle_connector_type: str = DEFAULT_CONNECTOR_TYPE,
    top_n: int = 3,
) -> dict[str, Any]:

    connector_type = (
        vehicle_connector_type.strip()
        or DEFAULT_CONNECTOR_TYPE
    )

    safe_range_km = calculate_api_safe_range(
        vehicle_class=vehicle_class,
        vehicle_range_km=vehicle_range_km,
        current_charge_pct=current_charge_pct,
    )

    enriched_candidates = enrich_candidates(
        route_geometry=route["geometry"],
        vehicle_connector_type=connector_type,
    )

    evaluated_candidates = evaluate_candidates(
        enriched_candidates,
        safe_range_km,
    )

    recommendation_candidates = []

    for candidate in evaluated_candidates:

        reliability = get_reliability_details(
            candidate["charger_id"]
        )

        recommendation_candidates.append(
            ChargerCandidate(
                charger_id=candidate["charger_id"],
                name=candidate["name"],
                city=candidate["city"],
                state=candidate["state"],
                latitude=candidate["latitude"],
                longitude=candidate["longitude"],
                route_progress_km=candidate[
                    "route_progress_km"
                ],
                road_access_km=candidate[
                    "road_access_km"
                ],
                required_distance_km=candidate[
                    "required_distance_km"
                ],
                range_safe=candidate["range_safe"],
                reliability_score=reliability[
                    "reliability_score"
                ],
                availability_score=75.0,
                trust_score=70.0,
                connector_compatibility=candidate.get(
                    "connector_compatibility",
                    "UNKNOWN",
                ),
            )
        )

    recommendations = recommend(
        recommendation_candidates,
        top_n=top_n,
    )

    return {
        "safe_range_km": round(
            safe_range_km,
            2,
        ),
        "candidate_count": len(
            enriched_candidates
        ),
        "safe_candidate_count": sum(
            1
            for candidate in evaluated_candidates
            if candidate["range_safe"]
        ),
        "recommendations": recommendations,
    }