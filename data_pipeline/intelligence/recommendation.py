from dataclasses import dataclass


@dataclass
class ChargerCandidate:
    charger_id: str
    name: str
    city: str | None
    state: str | None

    route_progress_km: float
    road_access_km: float
    required_distance_km: float

    range_safe: bool

    reliability_score: float
    availability_score: float
    trust_score: float

    connector_compatible: bool = True

    final_score: float = 0.0


def calculate_distance_score(
    road_access_km: float,
) -> float:
    """
    Stable score based only on this charger's road-access distance.
    Smaller distance = better score.
    """

    score = 100.0 / (
        1.0 + road_access_km
    )

    return round(score, 2)


def calculate_final_score(
    candidate: ChargerCandidate,
) -> float:

    # Safety gates
    if not candidate.range_safe:
        return 0.0

    if not candidate.connector_compatible:
        return 0.0

    distance_score = calculate_distance_score(
        candidate.road_access_km
    )

    score = (
        candidate.reliability_score * 0.40
        + distance_score * 0.20
        + candidate.availability_score * 0.20
        + candidate.trust_score * 0.20
    )

    return round(score, 2)


def rank_chargers(
    candidates: list[ChargerCandidate],
) -> list[ChargerCandidate]:

    safe_candidates = [
        candidate
        for candidate in candidates
        if candidate.range_safe
        and candidate.connector_compatible
    ]

    for candidate in safe_candidates:
        candidate.final_score = calculate_final_score(
            candidate
        )

    safe_candidates.sort(
        key=lambda candidate: (
            -candidate.final_score,
            candidate.road_access_km,
            -candidate.reliability_score,
        )
    )

    return safe_candidates


def get_recommendation_reasons(
    candidate: ChargerCandidate,
) -> list[str]:

    reasons = []

    reasons.append(
        "Within the vehicle's safe reachable range"
    )

    if candidate.road_access_km <= 1:
        reasons.append(
            "Very low road access distance"
        )
    elif candidate.road_access_km <= 3:
        reasons.append(
            "Low road access distance"
        )

    if candidate.reliability_score >= 85:
        reasons.append(
            "High reliability"
        )
    elif candidate.reliability_score >= 70:
        reasons.append(
            "Good reliability"
        )

    if candidate.availability_score >= 80:
        reasons.append(
            "High availability"
        )

    if candidate.trust_score >= 80:
        reasons.append(
            "High user trust"
        )

    return reasons


def recommend(
    candidates: list[ChargerCandidate],
    top_n: int = 3,
) -> list[dict]:

    ranked = rank_chargers(candidates)

    results = []

    for rank, candidate in enumerate(
        ranked[:top_n],
        start=1,
    ):

        results.append(
            {
                "rank": rank,
                "charger_id": candidate.charger_id,
                "name": candidate.name,
                "city": candidate.city,
                "state": candidate.state,

                "route_progress_km": round(
                    candidate.route_progress_km,
                    2,
                ),

                "road_access_km": round(
                    candidate.road_access_km,
                    2,
                ),

                "required_distance_km": round(
                    candidate.required_distance_km,
                    2,
                ),

                "range_safe": candidate.range_safe,

                "reliability_score": round(
                    candidate.reliability_score,
                    2,
                ),

                "availability_score": round(
                    candidate.availability_score,
                    2,
                ),

                "trust_score": round(
                    candidate.trust_score,
                    2,
                ),

                "connector_compatible": (
                    candidate.connector_compatible
                ),

                "final_score": candidate.final_score,

                "reasons": get_recommendation_reasons(
                    candidate
                ),
            }
        )

    return results