import json
from pathlib import Path
from collections import Counter


INPUT_FILE = Path("data/processed/chargers_clean.json")


ALLOWED_STATUSES = {
    "available",
    "occupied",
    "faulted",
    "offline",
    "unknown",
}


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        chargers = json.load(file)

    print(f"Total records: {len(chargers)}")
    print()

    # --------------------------------------------------
    # 1. Required field validation
    # --------------------------------------------------

    required_fields = [
        "charger_id",
        "source",
        "source_id",
        "name",
        "latitude",
        "longitude",
        "status",
    ]

    missing_counts = Counter()

    for charger in chargers:
        for field in required_fields:
            value = charger.get(field)

            if value is None or value == "":
                missing_counts[field] += 1

    print("Missing required fields:")
    for field in required_fields:
        print(
            f"  {field}: "
            f"{missing_counts[field]}"
        )

    print()

    # --------------------------------------------------
    # 2. Duplicate charger IDs
    # --------------------------------------------------

    charger_ids = [
        charger.get("charger_id")
        for charger in chargers
    ]

    duplicates = [
        charger_id
        for charger_id, count
        in Counter(charger_ids).items()
        if count > 1
    ]

    print(
        f"Duplicate charger IDs: "
        f"{len(duplicates)}"
    )

    # --------------------------------------------------
    # 3. Coordinate validation
    # --------------------------------------------------

    invalid_coordinates = []

    for charger in chargers:
        lat = charger.get("latitude")
        lon = charger.get("longitude")

        if lat is None or lon is None:
            invalid_coordinates.append(
                charger["charger_id"]
            )
            continue

        if not (-90 <= lat <= 90):
            invalid_coordinates.append(
                charger["charger_id"]
            )
            continue

        if not (-180 <= lon <= 180):
            invalid_coordinates.append(
                charger["charger_id"]
            )

    print(
        f"Invalid coordinates: "
        f"{len(invalid_coordinates)}"
    )

    # --------------------------------------------------
    # 4. Status validation
    # --------------------------------------------------

    invalid_statuses = []

    for charger in chargers:
        status = charger.get("status")

        if status not in ALLOWED_STATUSES:
            invalid_statuses.append(
                (
                    charger["charger_id"],
                    status,
                )
            )

    print(
        f"Invalid statuses: "
        f"{len(invalid_statuses)}"
    )

    # --------------------------------------------------
    # 5. Missing city
    # --------------------------------------------------

    missing_city = sum(
        1
        for charger in chargers
        if not charger.get("city")
    )

    print(
        f"Missing city: "
        f"{missing_city}"
    )

    # --------------------------------------------------
    # 6. Missing state
    # --------------------------------------------------

    missing_state = sum(
        1
        for charger in chargers
        if not charger.get("state")
    )

    print(
        f"Missing state: "
        f"{missing_state}"
    )

    # --------------------------------------------------
    # 7. Missing power
    # --------------------------------------------------

    missing_power = sum(
        1
        for charger in chargers
        if charger.get("power_kw") is None
    )

    print(
        f"Missing power_kw: "
        f"{missing_power}"
    )

    # --------------------------------------------------
    # 8. State consistency
    # --------------------------------------------------

    states = Counter(
        charger.get("state")
        for charger in chargers
        if charger.get("state")
    )

    print()
    print("Top states:")

    for state, count in states.most_common(15):
        print(
            f"  {state}: {count}"
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    has_errors = (
        len(duplicates) > 0
        or len(invalid_coordinates) > 0
        or len(invalid_statuses) > 0
    )

    print()

    if has_errors:
        print(
            "VALIDATION RESULT: FAILED"
        )
    else:
        print(
            "VALIDATION RESULT: PASSED"
        )


if __name__ == "__main__":
    main()