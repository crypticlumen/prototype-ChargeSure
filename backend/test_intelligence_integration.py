import asyncio

from app.services.osrm_service import OSRMService
from app.services.intelligence_adapter import (
    build_intelligent_recommendations,
)


async def main():
    route = await OSRMService().get_route(
        23.0225,
        72.5714,
        22.3072,
        73.1812,
    )

    result = build_intelligent_recommendations(
        route=route,
        vehicle_class="2W",
        vehicle_range_km=80.0,
        current_charge_pct=42.0,
        vehicle_connector_type="CCS",
        top_n=3,
    )

    print()
    print("INTELLIGENCE INTEGRATION TEST")
    print("=" * 70)

    print(f"Route distance: {route['distance_km']:.2f} km")
    print(f"Route duration: {route['duration_minutes']:.2f} min")
    print(f"Safe range: {result['safe_range_km']:.2f} km")
    print(f"Candidates: {result['candidate_count']}")
    print(f"Safe candidates: {result['safe_candidate_count']}")

    print()
    print("RECOMMENDATIONS")
    print("=" * 70)

    for item in result["recommendations"]:
        print(
            f"#{item['rank']} "
            f"{item['charger_id']} | "
            f"{item['name']} | "
            f"final={item['final_score']} | "
            f"reliability={item['reliability_score']} | "
            f"access={item['road_access_km']} km | "
            f"connector={item['connector_compatibility']}"
        )


if __name__ == "__main__":
    asyncio.run(main())