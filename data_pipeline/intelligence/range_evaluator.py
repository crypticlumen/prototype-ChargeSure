from typing import Iterable


def calculate_safe_range_km(
    battery_percent: float,
    battery_capacity_kwh: float,
    efficiency_wh_per_km: float,
    safety_reserve_percent: float = 20.0,
) -> float:
    if not 0 <= battery_percent <= 100:
        raise ValueError(
            "battery_percent must be between 0 and 100"
        )

    if battery_capacity_kwh <= 0:
        raise ValueError(
            "battery_capacity_kwh must be greater than 0"
        )

    if efficiency_wh_per_km <= 0:
        raise ValueError(
            "efficiency_wh_per_km must be greater than 0"
        )

    if not 0 <= safety_reserve_percent < 100:
        raise ValueError(
            "safety_reserve_percent must be between 0 and 100"
        )

    available_energy_kwh = (
        battery_capacity_kwh
        * battery_percent
        / 100
    )

    estimated_range_km = (
        available_energy_kwh * 1000
        / efficiency_wh_per_km
    )

    safe_range_km = (
        estimated_range_km
        * (1 - safety_reserve_percent / 100)
    )

    return safe_range_km


def evaluate_candidate(
    candidate: dict,
    safe_range_km: float,
) -> dict:

    required_distance_km = (
        candidate["route_progress_km"]
        + candidate["road_access_km"]
    )

    range_safe = (
        required_distance_km <= safe_range_km
    )

    return {
        **candidate,
        "required_distance_km": round(
            required_distance_km,
            2,
        ),
        "range_safe": range_safe,
    }


def evaluate_candidates(
    candidates: Iterable[dict],
    safe_range_km: float,
) -> list[dict]:

    return [
        evaluate_candidate(
            candidate,
            safe_range_km,
        )
        for candidate in candidates
    ]