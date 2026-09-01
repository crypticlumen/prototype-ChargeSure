from dataclasses import dataclass


@dataclass
class RecommendationCandidate:
    charger_id: str
    name: str
    city: str | None
    state: str | None

    route_progress_km: float
    road_access_km: float

    range_safe: bool

    reliability_score: float
    availability_score: float
    trust_score: float

    connector_compatible: bool = True


def calculate_distance_score(
    road_access_km: float,
) -> float:
    """
    Converts road access distance into a stable score.

    0 km access = 100
    Increasing distance lowers the score.

    This avoids making the score depend on which
    other chargers happen to be in the candidate set.
    """

    score = 100.0 / (
        1.0 + road_access_km
    )

    return round(score, 2)


def calculate_final_score(
    candidate: RecommendationCandidate,
) -> float:

    # Safety gates.
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


def rank_candidates(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:

    safe = [
        candidate
        for candidate in candidates
        if candidate.range_safe
        and candidate.connector_compatible
    ]

    for candidate in safe:
        candidate.final_score = calculate_final_score(
            candidate
        )

    safe.sort(
        key=lambda item: (
            -item.final_score,
            item.road_access_km,
            -item.reliability_score,
        )
    )

    return safe


def build_recommendations(
    candidates: list[RecommendationCandidate],
    top_n: int = 3,
) -> list[dict]:

    ranked = rank_candidates(candidates)

    results = []

    for rank, candidate in enumerate(
        ranked[:top_n],
        start=1,
    ):

        reasons = [
            "Within safe vehicle range"
        ]

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
                "final_score": candidate.final_score,
                "range_safe": candidate.range_safe,
                "connector_compatible":
                    candidate.connector_compatible,
                "reasons": reasons,
            }
        )

    return results