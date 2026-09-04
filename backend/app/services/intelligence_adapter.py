from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import psycopg2

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
    get_operational_signals,
)

from app.config import get_settings
from app.services.grid_slot_recommender import (
    grid_slot_recommender,
)


DEFAULT_CONNECTOR_TYPE = "CCS"
DEFAULT_SAFETY_RESERVE_PERCENT = 20.0

VEHICLE_EFFICIENCY_WH_PER_KM = {
    "2W": 45.0,
    "3W": 45.0,
    "4W": 45.0,
}

USER_TIMEZONE = ZoneInfo("Asia/Kolkata")

CHARGER_ACCESS_SPEED_KMPH = 25.0

DEFAULT_CHARGE_DURATION_MINUTES = 30

MAX_SLOT_SEARCH_ATTEMPTS = 12


def calculate_api_safe_range(
    vehicle_class: str,
    vehicle_range_km: float,
    current_charge_pct: float,
) -> float:
    """
    Calculate safe driving range for the current battery level.

    A 20% safety reserve is always maintained.
    """

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
        vehicle_range_km
        * efficiency
        / 1000.0
    )

    return calculate_safe_range_km(
        battery_percent=current_charge_pct,
        battery_capacity_kwh=(
            equivalent_battery_capacity_kwh
        ),
        efficiency_wh_per_km=efficiency,
        safety_reserve_percent=(
            DEFAULT_SAFETY_RESERVE_PERCENT
        ),
    )


def _get_database_url() -> str:
    """
    Get the active ChargeSure PostgreSQL URL.
    """

    settings = get_settings()
    return settings.database_url


def _get_db_connection():
    """
    Open a PostgreSQL connection for booking checks.
    """

    return psycopg2.connect(
        _get_database_url()
    )


def _find_conflicting_booking(
    charger_id: str,
    slot_start: datetime,
    slot_end: datetime,
) -> Optional[tuple[datetime, datetime]]:
    """
    Return the first confirmed booking that overlaps
    the proposed slot.
    """

    query = """
        SELECT slot_start, slot_end
        FROM bookings
        WHERE charger_id = %s
          AND status = 'CONFIRMED'
          AND slot_start < %s
          AND slot_end > %s
        ORDER BY slot_start ASC
        LIMIT 1
    """

    connection = None
    cursor = None

    try:
        connection = _get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            query,
            (
                charger_id,
                slot_end,
                slot_start,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row[0], row[1]

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def _ensure_timezone_aware(
    value: datetime,
) -> datetime:
    """
    Normalize a datetime into Asia/Kolkata.
    """

    if value.tzinfo is None:
        return value.replace(
            tzinfo=USER_TIMEZONE
        )

    return value.astimezone(
        USER_TIMEZONE
    )


def _normalize_departure_time(
    departure_time: Optional[datetime],
) -> datetime:
    """
    Normalize departure time into Asia/Kolkata.

    None means leave now.
    """

    if departure_time is None:
        return datetime.now(
            USER_TIMEZONE
        )

    return _ensure_timezone_aware(
        departure_time
    )


def _calculate_charger_arrival(
    route: dict[str, Any],
    candidate: dict[str, Any],
    route_start_time: datetime,
) -> datetime:
    """
    Estimate arrival time at a specific charger.
    """

    route_distance_km = float(
        route.get("distance_km") or 0.0
    )

    route_duration_minutes = float(
        route.get("duration_minutes") or 0.0
    )

    route_progress_km = max(
        0.0,
        float(
            candidate.get(
                "route_progress_km"
            )
            or 0.0
        ),
    )

    road_access_km = max(
        0.0,
        float(
            candidate.get(
                "road_access_km"
            )
            or 0.0
        ),
    )

    if route_distance_km <= 0:
        main_route_minutes = 0.0
    else:
        progress_ratio = min(
            route_progress_km
            / route_distance_km,
            1.0,
        )

        main_route_minutes = (
            route_duration_minutes
            * progress_ratio
        )

    access_minutes = (
        road_access_km
        / CHARGER_ACCESS_SPEED_KMPH
        * 60.0
    )

    return route_start_time + timedelta(
        minutes=(
            main_route_minutes
            + access_minutes
        )
    )


def _recommend_available_slot(
    charger_id: str,
    earliest_arrival: datetime,
) -> tuple[
    datetime,
    datetime,
    bool,
]:
    """
    Find a grid-aware slot that does not overlap
    an existing confirmed booking.
    """

    search_start = _ensure_timezone_aware(
        earliest_arrival
    )

    for _ in range(
        MAX_SLOT_SEARCH_ATTEMPTS
    ):
        (
            slot_start,
            slot_end,
            grid_aware,
        ) = grid_slot_recommender.recommend_slot(
            earliest_arrival=search_start,
            charge_duration_minutes=(
                DEFAULT_CHARGE_DURATION_MINUTES
            ),
        )

        slot_start = _ensure_timezone_aware(
            slot_start
        )

        slot_end = _ensure_timezone_aware(
            slot_end
        )

        conflict = _find_conflicting_booking(
            charger_id=charger_id,
            slot_start=slot_start,
            slot_end=slot_end,
        )

        if conflict is None:
            return (
                slot_start,
                slot_end,
                grid_aware,
            )

        _, conflict_end = conflict

        conflict_end = _ensure_timezone_aware(
            conflict_end
        )

        next_start = max(
            search_start,
            conflict_end,
            slot_end,
        )

        search_start = (
            next_start
            + timedelta(seconds=1)
        )

    fallback_start = search_start

    fallback_end = (
        fallback_start
        + timedelta(
            minutes=DEFAULT_CHARGE_DURATION_MINUTES
        )
    )

    return (
        fallback_start,
        fallback_end,
        False,
    )


def _normalize_confidence(
    confidence: Any,
) -> str:
    """
    Normalize evidence confidence into one of:

        High
        Medium
        Low
    """

    if confidence is None:
        return "Medium"

    value = str(
        confidence
    ).strip().lower()

    if value in {
        "high",
        "very high",
        "excellent",
    }:
        return "High"

    if value in {
        "medium",
        "moderate",
        "average",
    }:
        return "Medium"

    if value in {
        "low",
        "poor",
        "weak",
    }:
        return "Low"

    return (
        str(confidence)
        .strip()
        .capitalize()
    )


def _connector_is_compatible(
    candidate: dict[str, Any],
) -> bool:
    """
    Determine whether the backend considers the charger
    connector compatible.

    UNKNOWN is intentionally treated as usable for the
    scheduling pipeline because the ranking engine assigns
    it a neutral connector score.
    """

    value = candidate.get(
        "connector_compatibility"
    )

    if value is None:
        return True

    normalized = str(
        value
    ).strip().lower()

    if normalized in {
        "incompatible",
        "not compatible",
        "false",
        "no",
    }:
        return False

    return True


def _classify_reliability(
    reliability_score: float,
) -> str:
    """
    Convert reliability score into a quality label.

    This represents reliability quality, NOT prediction
    confidence.
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


def _build_recommendation_reason(
    recommendation: dict[str, Any],
    ranking_index: int,
    confidence: str,
) -> str:
    """
    Build a data-driven explanation for why this charger
    received its recommendation position.

    Prediction confidence is kept separate from the
    reliability-quality description.
    """

    reliability = float(
        recommendation.get(
            "reliability_score"
        )
        or 0.0
    )

    reliability_quality = _classify_reliability(
        reliability
    )

    route_distance = float(
        recommendation.get(
            "distance_from_origin_km"
        )
        or recommendation.get(
            "required_distance_km"
        )
        or 0.0
    )

    connector_status = str(
        recommendation.get(
            "connector_status",
            "Unknown",
        )
    ).strip().lower()

    connector_compatible = (
        connector_status == "compatible"
        or _connector_is_compatible(
            recommendation
        )
    )

    grid_optimized = bool(
        recommendation.get(
            "is_grid_aware_recommended",
            False,
        )
    )

    parts: list[str] = []

    # --------------------------------------------------
    # Reliability quality
    # --------------------------------------------------

    if reliability >= 85:
        parts.append(
            f"high reliability ({reliability:.1f}/100)"
        )

    elif reliability >= 70:
        parts.append(
            f"good reliability ({reliability:.1f}/100)"
        )

    elif reliability >= 40:
        parts.append(
            f"moderate reliability ({reliability:.1f}/100)"
        )

    elif reliability >= 20:
        parts.append(
            f"low reliability ({reliability:.1f}/100)"
        )

    else:
        parts.append(
            f"very low reliability ({reliability:.1f}/100)"
        )

    # --------------------------------------------------
    # Connector
    # --------------------------------------------------

    if connector_compatible:
        parts.append(
            "compatible connector"
        )

    elif connector_status in {
        "not compatible",
        "incompatible",
    }:
        parts.append(
            "connector is not compatible"
        )

    else:
        parts.append(
            "connector compatibility could not be verified"
        )

    # --------------------------------------------------
    # Route access
    # --------------------------------------------------

    if route_distance > 0:

        if route_distance <= 7:
            parts.append(
                "very low route deviation"
            )

        elif route_distance <= 12:
            parts.append(
                "low route deviation"
            )

        elif route_distance <= 25:
            parts.append(
                "reasonable route distance"
            )

    # --------------------------------------------------
    # Grid
    # --------------------------------------------------

    if grid_optimized:
        parts.append(
            "grid-optimized slot"
        )

    # --------------------------------------------------
    # Ranking context
    # --------------------------------------------------

    if ranking_index == 0:
        prefix = "Best overall match"
    elif ranking_index == 1:
        prefix = "Strong alternative"
    else:
        prefix = "Good alternative"

    sentence = (
        prefix
        + ": "
        + ", ".join(parts[:-1])
    )

    if len(parts) > 1:
        sentence += (
            f", and {parts[-1]}"
        )

    sentence += "."

    return sentence


def build_intelligent_recommendations(
    route: dict[str, Any],
    vehicle_class: str,
    vehicle_range_km: float,
    current_charge_pct: float,
    vehicle_connector_type: str = DEFAULT_CONNECTOR_TYPE,
    departure_time: Optional[datetime] = None,
    top_n: int = 3,
) -> dict[str, Any]:
    """
    Build the complete ChargeSure intelligent recommendation.

    Pipeline:

        Route
          ↓
        Departure time
          ↓
        Safe range
          ↓
        Charger candidates
          ↓
        Road-access enrichment
          ↓
        Range safety
          ↓
        Reliability
          ↓
        Connector compatibility
          ↓
        Operational signals
          ↓
        Final ranking
          ↓
        Charger-specific ETA
          ↓
        Grid-aware slot
          ↓
        Booking conflict check
          ↓
        Recommendation explanation
    """

    connector_type = (
        vehicle_connector_type.strip()
        or DEFAULT_CONNECTOR_TYPE
    )

    # --------------------------------------------------
    # Safe driving range
    # --------------------------------------------------

    safe_range_km = calculate_api_safe_range(
        vehicle_class=vehicle_class,
        vehicle_range_km=vehicle_range_km,
        current_charge_pct=current_charge_pct,
    )

    # --------------------------------------------------
    # Candidate discovery
    # --------------------------------------------------

    enriched_candidates = enrich_candidates(
        route_geometry=route["geometry"],
        vehicle_connector_type=connector_type,
    )

    # --------------------------------------------------
    # Range safety
    # --------------------------------------------------

    evaluated_candidates = evaluate_candidates(
        enriched_candidates,
        safe_range_km,
    )

    # --------------------------------------------------
    # Departure time
    # --------------------------------------------------

    route_start_time = _normalize_departure_time(
        departure_time
    )

    # --------------------------------------------------
    # Prepare recommendation candidates
    # --------------------------------------------------

    recommendation_candidates = []

    schedule_by_charger: dict[
        str,
        dict[str, Any],
    ] = {}

    for candidate in evaluated_candidates:

        charger_id = candidate["charger_id"]

        # ----------------------------------------------
        # Reliability
        # ----------------------------------------------

        reliability = get_reliability_details(
            charger_id
        )

        reliability_score = float(
            reliability.get(
                "reliability_score",
                0.0,
            )
            or 0.0
        )

        reliability_confidence = _normalize_confidence(
            reliability.get(
                "confidence"
            )
        )

        reliability_quality = _classify_reliability(
            reliability_score
        )

        # ----------------------------------------------
        # Operational signals
        # ----------------------------------------------

        operational = get_operational_signals(
            charger_id
        )

        # ----------------------------------------------
        # Candidate object
        # ----------------------------------------------

        recommendation_candidates.append(
            ChargerCandidate(
                charger_id=charger_id,

                name=candidate["name"],

                city=candidate["city"],

                state=candidate["state"],

                latitude=candidate["latitude"],

                longitude=candidate["longitude"],

                route_progress_km=(
                    candidate["route_progress_km"]
                ),

                road_access_km=(
                    candidate["road_access_km"]
                ),

                required_distance_km=(
                    candidate["required_distance_km"]
                ),

                range_safe=(
                    candidate["range_safe"]
                ),

                reliability_score=(
                    reliability_score
                ),

                availability_score=float(
                    operational.get(
                        "availability_score",
                        50.0,
                    )
                    or 0.0
                ),

                trust_score=float(
                    operational.get(
                        "trust_score",
                        50.0,
                    )
                    or 0.0
                ),

                connector_compatibility=(
                    candidate.get(
                        "connector_compatibility",
                        "UNKNOWN",
                    )
                ),
            )
        )

        # ----------------------------------------------
        # Charger-specific ETA
        # ----------------------------------------------

        charger_arrival = _calculate_charger_arrival(
            route=route,
            candidate=candidate,
            route_start_time=route_start_time,
        )

        # ----------------------------------------------
        # Grid + booking-aware slot
        # ----------------------------------------------

        (
            slot_start,
            slot_end,
            grid_aware,
        ) = _recommend_available_slot(
            charger_id=charger_id,
            earliest_arrival=charger_arrival,
        )

        schedule_by_charger[
            charger_id
        ] = {
            "recommended_slot_start": slot_start,
            "recommended_slot_end": slot_end,

            "is_grid_aware_recommended": (
                grid_aware
            ),

            "estimated_arrival": (
                charger_arrival
            ),

            # Prediction confidence is evidence confidence.
            "confidence_band": (
                reliability_confidence
            ),

            "reliability_confidence": (
                reliability_confidence
            ),

            # Reliability quality is the actual score band.
            "reliability_quality": (
                reliability_quality
            ),

            "connector_compatible": (
                _connector_is_compatible(
                    candidate
                )
            ),
        }

    # --------------------------------------------------
    # Final ranking
    # --------------------------------------------------

    recommendations = recommend(
        recommendation_candidates,
        top_n=top_n,
    )

    # --------------------------------------------------
    # Attach scheduling + intelligence details
    # --------------------------------------------------

    enriched_recommendations = []

    for index, recommendation in enumerate(
        recommendations
    ):

        charger_id = recommendation[
            "charger_id"
        ]

        schedule = schedule_by_charger.get(
            charger_id,
            {},
        )

        recommendation.update(
            schedule
        )

        recommendation[
            "recommendation_rank"
        ] = index + 1

        recommendation[
            "recommendation_label"
        ] = (
            "Best overall match"
            if index == 0
            else (
                "Strong alternative"
                if index == 1
                else "Good alternative"
            )
        )

        # Explicit connector status for API consumers.
        recommendation[
            "connector_status"
        ] = (
            "Compatible"
            if schedule.get(
                "connector_compatible",
                True,
            )
            else "Not compatible"
        )

        recommendation[
            "why_recommended"
        ] = _build_recommendation_reason(
            recommendation=recommendation,
            ranking_index=index,
            confidence=(
                schedule.get(
                    "reliability_confidence",
                    "Medium",
                )
            ),
        )

        # Preserve a clear user-facing label for
        # prediction confidence.
        recommendation[
            "prediction_confidence"
        ] = schedule.get(
            "reliability_confidence",
            "Medium",
        )

        enriched_recommendations.append(
            recommendation
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

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
            for candidate
            in evaluated_candidates
            if candidate["range_safe"]
        ),

        "departure_time": route_start_time,

        "recommendations": (
            enriched_recommendations
        ),
    }