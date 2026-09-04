from dataclasses import dataclass
from typing import List


@dataclass
class ChargerCandidate:
    charger_id: str
    name: str
    city: str | None
    state: str | None

    latitude: float
    longitude: float

    route_progress_km: float
    road_access_km: float
    required_distance_km: float

    range_safe: bool

    reliability_score: float
    availability_score: float = 50.0
    trust_score: float = 50.0

    connector_compatibility: str = "UNKNOWN"

    final_score: float = 0.0


def calculate_distance_score(
    road_access_km: float,
    max_access_km: float,
) -> float:
    """
    Smaller road access distance = better score.
    """

    if max_access_km <= 0:
        return 100.0

    score = (
        1.0
        - (
            road_access_km
            / max_access_km
        )
    ) * 100.0

    return max(
        0.0,
        min(100.0, score),
    )


def calculate_final_score(
    reliability_score: float,
    range_safe: bool,
    distance_score: float,
    availability_score: float,
    trust_score: float,
    connector_compatibility: str,
) -> float:
    """
    Calculate final charger score.

    Range safety is a hard safety gate.

    Connector compatibility:
        COMPATIBLE   -> positive signal
        UNKNOWN      -> neutral signal
        INCOMPATIBLE -> rejected before scoring

    Final score weights:
        Reliability  -> 40%
        Distance     -> 20%
        Availability -> 10%
        Trust        -> 10%
        Connector    -> 20%
    """

    if not range_safe:
        return 0.0

    if connector_compatibility == "INCOMPATIBLE":
        return 0.0

    if connector_compatibility == "COMPATIBLE":
        connector_score = 100.0
    else:
        connector_score = 50.0

    score = (
        reliability_score * 0.40
        + distance_score * 0.20
        + availability_score * 0.10
        + trust_score * 0.10
        + connector_score * 0.20
    )

    return round(
        score,
        2,
    )


def rank_chargers(
    candidates: List[ChargerCandidate],
) -> List[ChargerCandidate]:

    # --------------------------------------------------
    # Safety and compatibility gate
    # --------------------------------------------------

    eligible_candidates = [
        candidate
        for candidate in candidates
        if (
            candidate.range_safe
            and candidate.connector_compatibility
            != "INCOMPATIBLE"
        )
    ]

    if not eligible_candidates:
        return []

    # --------------------------------------------------
    # Determine maximum road-access distance
    # --------------------------------------------------

    max_access_km = max(
        candidate.road_access_km
        for candidate in eligible_candidates
    )

    # --------------------------------------------------
    # Calculate scores
    # --------------------------------------------------

    for candidate in eligible_candidates:
        distance_score = calculate_distance_score(
            candidate.road_access_km,
            max_access_km,
        )

        candidate.final_score = calculate_final_score(
            reliability_score=candidate.reliability_score,
            range_safe=candidate.range_safe,
            distance_score=distance_score,
            availability_score=candidate.availability_score,
            trust_score=candidate.trust_score,
            connector_compatibility=(
                candidate.connector_compatibility
            ),
        )

    # --------------------------------------------------
    # Sort
    # --------------------------------------------------

    eligible_candidates.sort(
        key=lambda candidate: (
            -candidate.final_score,
            candidate.road_access_km,
            candidate.route_progress_km,
        )
    )

    return eligible_candidates


def _reliability_quality(
    reliability_score: float,
) -> str:
    """
    Convert the numerical reliability score into a
    user-facing quality classification.

    This is intentionally separate from prediction
    confidence. A prediction may be low but highly
    confident based on available evidence.
    """

    score = max(
        0.0,
        min(100.0, reliability_score),
    )

    if score >= 85.0:
        return "High"

    if score >= 70.0:
        return "Good"

    if score >= 40.0:
        return "Moderate"

    if score >= 20.0:
        return "Low"

    return "Very low"


def get_recommendation_reason(
    candidate: ChargerCandidate,
) -> List[str]:

    reasons: List[str] = []

    if candidate.range_safe:
        reasons.append(
            "Within the vehicle's safe reachable range"
        )

    if candidate.connector_compatibility == "COMPATIBLE":
        reasons.append(
            "Connector compatible with vehicle"
        )

    elif candidate.connector_compatibility == "UNKNOWN":
        reasons.append(
            "Connector compatibility could not be verified"
        )

    if candidate.road_access_km <= 1.0:
        reasons.append(
            "Very low road access distance"
        )

    elif candidate.road_access_km <= 3.0:
        reasons.append(
            "Low road access distance"
        )

    reliability_quality = _reliability_quality(
        candidate.reliability_score
    )

    reasons.append(
        f"{reliability_quality} reliability "
        f"({candidate.reliability_score:.1f}/100)"
    )

    if candidate.availability_score >= 80:
        reasons.append(
            "High availability"
        )

    elif candidate.availability_score >= 60:
        reasons.append(
            "Moderate availability"
        )

    if candidate.trust_score >= 80:
        reasons.append(
            "Strong user trust"
        )

    elif candidate.trust_score >= 60:
        reasons.append(
            "Moderate user trust"
        )

    return reasons


def recommend(
    candidates: List[ChargerCandidate],
    top_n: int = 3,
) -> List[dict]:

    ranked = rank_chargers(
        candidates
    )

    recommendations = []

    for rank, candidate in enumerate(
        ranked[:top_n],
        start=1,
    ):

        reliability_quality = _reliability_quality(
            candidate.reliability_score
        )

        recommendations.append(
            {
                "rank": rank,
                "charger_id": candidate.charger_id,
                "name": candidate.name,
                "city": candidate.city,
                "state": candidate.state,
                "latitude": candidate.latitude,
                "longitude": candidate.longitude,

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

                "reliability_score": round(
                    candidate.reliability_score,
                    2,
                ),

                "reliability_quality": reliability_quality,

                "availability_score": round(
                    candidate.availability_score,
                    2,
                ),

                "trust_score": round(
                    candidate.trust_score,
                    2,
                ),

                "connector_compatibility": (
                    candidate.connector_compatibility
                ),

                "final_score": candidate.final_score,

                "range_safe": candidate.range_safe,

                "reasons": get_recommendation_reason(
                    candidate
                ),
            }
        )

    return recommendations