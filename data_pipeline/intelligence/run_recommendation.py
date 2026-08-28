from recommendation import (
    ChargerCandidate,
    recommend,
)

from reliability import (
    get_reliability_score,
)


# These are the real results you obtained
# from the current routing pipeline.

CURRENT_CANDIDATES = [
    {
        "charger_id": "OCM-502288",
        "name": "MobiLane Indrajit Online",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 0.00,
        "road_access_km": 4.31,
        "range_safe": True,
        "availability_score": 70,
        "trust_score": 65,
    },
    {
        "charger_id": "OCM-502314",
        "name": "MobiLane AMC Income Tax",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 0.00,
        "road_access_km": 2.75,
        "range_safe": True,
        "availability_score": 75,
        "trust_score": 70,
    },
    {
        "charger_id": "OCM-502283",
        "name": "MobiLane AMC Gulbai Tekra",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 1.09,
        "road_access_km": 3.24,
        "range_safe": True,
        "availability_score": 72,
        "trust_score": 68,
    },
    {
        "charger_id": "OCM-502321",
        "name": "MobiLane Mini - Universal Honda, Paldi",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 1.40,
        "road_access_km": 0.50,
        "range_safe": True,
        "availability_score": 90,
        "trust_score": 88,
    },
    {
        "charger_id": "OCM-502313",
        "name": "MobiLane AMC Kankariya",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 2.89,
        "road_access_km": 2.53,
        "range_safe": True,
        "availability_score": 78,
        "trust_score": 74,
    },
    {
        "charger_id": "OCM-502306",
        "name": "MobiLane AMC CTM",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 6.22,
        "road_access_km": 6.33,
        "range_safe": False,
        "availability_score": 65,
        "trust_score": 58,
    },
    {
        "charger_id": "OCM-502308",
        "name": "MobiLane AMC Govindwadi",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 6.31,
        "road_access_km": 1.92,
        "range_safe": True,
        "availability_score": 82,
        "trust_score": 80,
    },
    {
        "charger_id": "OCM-502309",
        "name": "MobiLane AMC Narol GB/T",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 7.25,
        "road_access_km": 0.31,
        "range_safe": True,
        "availability_score": 92,
        "trust_score": 90,
    },
    {
        "charger_id": "OCM-502299",
        "name": "MobiLane A K Tyre",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 8.00,
        "road_access_km": 2.29,
        "range_safe": True,
        "availability_score": 78,
        "trust_score": 72,
    },
    {
        "charger_id": "OCM-502298",
        "name": "MobiLane A K Tyre",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "route_progress_km": 8.00,
        "road_access_km": 2.29,
        "range_safe": True,
        "availability_score": 78,
        "trust_score": 72,
    },
]


def main():

    candidates = []

    for item in CURRENT_CANDIDATES:

        candidates.append(
            ChargerCandidate(
                charger_id=item["charger_id"],
                name=item["name"],
                city=item["city"],
                state=item["state"],
                route_progress_km=item[
                    "route_progress_km"
                ],
                road_access_km=item[
                    "road_access_km"
                ],
                range_safe=item[
                    "range_safe"
                ],
                reliability_score=get_reliability_score(
                    item["charger_id"]
                ),
                availability_score=item[
                    "availability_score"
                ],
                trust_score=item[
                    "trust_score"
                ],
            )
        )

    results = recommend(
        candidates,
        top_n=3,
    )

    print("CHARGESURE RECOMMENDATIONS")
    print("=" * 100)

    if not results:
        print("No safe charger found.")
        return

    for result in results:

        print()
        print(
            f"#{result['rank']} "
            f"{result['name']}"
        )

        print(
            f"   Charger ID: "
            f"{result['charger_id']}"
        )

        print(
            f"   Final Score: "
            f"{result['final_score']}"
        )

        print(
            f"   Reliability: "
            f"{result['reliability_score']}"
        )

        print(
            f"   Route progress: "
            f"{result['route_progress_km']} km"
        )

        print(
            f"   Road access: "
            f"{result['road_access_km']} km"
        )

        print(
            f"   Range safe: "
            f"{result['range_safe']}"
        )

        print("   Why:")

        for reason in result["reasons"]:
            print(f"     ✓ {reason}")


if __name__ == "__main__":
    main()