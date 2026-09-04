import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

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
    get_operational_signals,
    get_reliability_score,
)


# =========================================================
# Vehicle configuration
# =========================================================

DEFAULT_BATTERY_PERCENT = 42.0
DEFAULT_BATTERY_CAPACITY_KWH = 3.2
DEFAULT_EFFICIENCY_WH_PER_KM = 45.0
DEFAULT_SAFETY_RESERVE_PERCENT = 20.0

DEFAULT_CONNECTOR_TYPE = "CCS"

# Ahmedabad -> Vadodara
DEFAULT_ORIGIN_LAT = 23.0225
DEFAULT_ORIGIN_LNG = 72.5714

DEFAULT_DESTINATION_LAT = 22.3072
DEFAULT_DESTINATION_LNG = 73.1812

DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"


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

    parser.add_argument(
        "--origin-lat",
        type=float,
        default=DEFAULT_ORIGIN_LAT,
    )

    parser.add_argument(
        "--origin-lng",
        type=float,
        default=DEFAULT_ORIGIN_LNG,
    )

    parser.add_argument(
        "--destination-lat",
        type=float,
        default=DEFAULT_DESTINATION_LAT,
    )

    parser.add_argument(
        "--destination-lng",
        type=float,
        default=DEFAULT_DESTINATION_LNG,
    )

    parser.add_argument(
        "--battery-percent",
        type=float,
        default=DEFAULT_BATTERY_PERCENT,
    )

    parser.add_argument(
        "--battery-capacity-kwh",
        type=float,
        default=DEFAULT_BATTERY_CAPACITY_KWH,
    )

    parser.add_argument(
        "--efficiency-wh-per-km",
        type=float,
        default=DEFAULT_EFFICIENCY_WH_PER_KM,
    )

    parser.add_argument(
        "--safety-reserve-percent",
        type=float,
        default=DEFAULT_SAFETY_RESERVE_PERCENT,
    )

    return parser.parse_args()


# =========================================================
# OSRM route
# =========================================================

def get_osrm_route(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
) -> dict:
    """
    Fetch the current road route from OSRM.

    Returns a GeoJSON LineString geometry suitable for
    candidate_repository.py.
    """

    base_url = os.getenv(
        "OSRM_BASE_URL",
        DEFAULT_OSRM_BASE_URL,
    ).rstrip("/")

    coordinates = (
        f"{origin_lng},{origin_lat};"
        f"{destination_lng},{destination_lat}"
    )

    query = urllib.parse.urlencode(
        {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }
    )

    url = (
        f"{base_url}/route/v1/driving/"
        f"{coordinates}?{query}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ChargeSure/1.0",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            payload = response.read().decode("utf-8")

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"OSRM returned HTTP {exc.code}."
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach OSRM: {exc.reason}"
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            "OSRM request timed out."
        ) from exc

    try:
        data = json.loads(payload)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "OSRM returned invalid JSON."
        ) from exc

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM routing failed: "
            f"{data.get('message', data.get('code', 'unknown error'))}"
        )

    routes = data.get("routes", [])

    if not routes:
        raise RuntimeError(
            "OSRM returned no route."
        )

    route = routes[0]

    geometry = route.get("geometry")

    if not isinstance(geometry, dict):
        raise RuntimeError(
            "OSRM route does not contain a valid GeoJSON geometry."
        )

    if geometry.get("type") != "LineString":
        raise RuntimeError(
            f"Unexpected OSRM geometry type: "
            f"{geometry.get('type')!r}"
        )

    coordinates = geometry.get("coordinates", [])

    if len(coordinates) < 2:
        raise RuntimeError(
            "OSRM returned an unusable route geometry."
        )

    return geometry


# =========================================================
# Validation helpers
# =========================================================

def validate_vehicle_inputs(
    battery_percent: float,
    battery_capacity_kwh: float,
    efficiency_wh_per_km: float,
    safety_reserve_percent: float,
):
    if not 0.0 <= battery_percent <= 100.0:
        raise ValueError(
            "battery_percent must be between 0 and 100."
        )

    if battery_capacity_kwh <= 0:
        raise ValueError(
            "battery_capacity_kwh must be greater than 0."
        )

    if efficiency_wh_per_km <= 0:
        raise ValueError(
            "efficiency_wh_per_km must be greater than 0."
        )

    if not 0.0 <= safety_reserve_percent < 100.0:
        raise ValueError(
            "safety_reserve_percent must be between 0 and 100."
        )


# =========================================================
# Main pipeline
# =========================================================

def main():
    args = parse_args()

    vehicle_connector_type = args.connector.strip()

    if not vehicle_connector_type:
        raise ValueError(
            "Vehicle connector type cannot be empty."
        )

    validate_vehicle_inputs(
        battery_percent=args.battery_percent,
        battery_capacity_kwh=args.battery_capacity_kwh,
        efficiency_wh_per_km=args.efficiency_wh_per_km,
        safety_reserve_percent=args.safety_reserve_percent,
    )

    # -----------------------------------------------------
    # Fetch road route
    # -----------------------------------------------------

    route_geometry = get_osrm_route(
        origin_lat=args.origin_lat,
        origin_lng=args.origin_lng,
        destination_lat=args.destination_lat,
        destination_lng=args.destination_lng,
    )

    route_points = len(
        route_geometry.get(
            "coordinates",
            [],
        )
    )

    # -----------------------------------------------------
    # Calculate vehicle safe range
    # -----------------------------------------------------

    safe_range_km = calculate_safe_range_km(
        battery_percent=args.battery_percent,
        battery_capacity_kwh=args.battery_capacity_kwh,
        efficiency_wh_per_km=args.efficiency_wh_per_km,
        safety_reserve_percent=args.safety_reserve_percent,
    )

    # -----------------------------------------------------
    # Load and enrich route candidates
    # -----------------------------------------------------

    enriched = enrich_candidates(
        route_geometry=route_geometry,
        vehicle_connector_type=vehicle_connector_type,
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

        charger_id = candidate["charger_id"]

        connector_status = candidate.get(
            "connector_compatibility",
            "UNKNOWN",
        )

        # ---------------------------------------------
        # Live reliability intelligence
        # ---------------------------------------------

        reliability_score = get_reliability_score(
            charger_id
        )

        operational = get_operational_signals(
            charger_id
        )

        availability_score = operational.get(
            "availability_score",
            50.0,
        )

        trust_score = operational.get(
            "trust_score",
            50.0,
        )

        recommendation_candidate = ChargerCandidate(
            charger_id=charger_id,

            name=candidate[
                "name"
            ],

            city=candidate[
                "city"
            ],

            state=candidate[
                "state"
            ],

            # FIX:
            # ChargerCandidate requires latitude/longitude.
            latitude=candidate[
                "latitude"
            ],

            longitude=candidate[
                "longitude"
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

            reliability_score=reliability_score,

            availability_score=availability_score,

            trust_score=trust_score,

            connector_compatibility=connector_status,
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

    print("=" * 110)

    print(
        f"Origin: "
        f"{args.origin_lat:.5f}, "
        f"{args.origin_lng:.5f}"
    )

    print(
        f"Destination: "
        f"{args.destination_lat:.5f}, "
        f"{args.destination_lng:.5f}"
    )

    print(
        f"OSRM route points: "
        f"{route_points}"
    )

    print(
        f"Vehicle connector: "
        f"{vehicle_connector_type}"
    )

    print(
        f"Battery: "
        f"{args.battery_percent:.0f}%"
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

    print("=" * 110)

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

        operational = get_operational_signals(
            result["charger_id"]
        )

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
            f"   Availability: "
            f"{result['availability_score']}"
        )

        print(
            f"   Trust: "
            f"{result['trust_score']}"
        )

        print(
            f"   Crowd reports: "
            f"{operational.get('crowd_report_count', 0)}"
        )

        print(
            f"   Crowd signal: "
            f"{operational.get('crowd_signal_score', 50.0)}"
        )

        print(
            f"   Positive reports: "
            f"{operational.get('positive_report_ratio', 0.0) * 100:.2f}%"
        )

        print(
            f"   Negative reports: "
            f"{operational.get('negative_report_ratio', 0.0) * 100:.2f}%"
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

        for reason in result["reasons"]:
            print(
                f"     ✓ {reason}"
            )


if __name__ == "__main__":
    main()