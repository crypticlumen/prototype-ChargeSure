import json
from pathlib import Path
from collections import Counter


INPUT_FILE = Path(
    "data/processed/chargers_normalized.json"
)


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        chargers = json.load(file)

    print(f"Total records: {len(chargers)}")
    print("=" * 60)

    required_fields = [
        "charger_id",
        "source",
        "source_id",
        "name",
        "latitude",
        "longitude",
        "status",
    ]

    errors = []

    # ---------------------------------------
    # Required fields
    # ---------------------------------------

    for charger in chargers:

        for field in required_fields:

            value = charger.get(field)

            if value is None or value == "":
                errors.append(
                    f"{charger.get('charger_id')}: "
                    f"missing {field}"
                )

    # ---------------------------------------
    # Duplicate IDs
    # ---------------------------------------

    ids = [
        charger.get("charger_id")
        for charger in chargers
    ]

    duplicate_ids = [
        charger_id
        for charger_id, count
        in Counter(ids).items()
        if count > 1
    ]

    # ---------------------------------------
    # Coordinates
    # ---------------------------------------

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

        if not (-180 <= lon <= 180):
            invalid_coordinates.append(
                charger["charger_id"]
            )

    # ---------------------------------------
    # Report
    # ---------------------------------------

    print(
        f"Required field errors: "
        f"{len(errors)}"
    )

    print(
        f"Duplicate IDs: "
        f"{len(duplicate_ids)}"
    )

    print(
        f"Invalid coordinates: "
        f"{len(invalid_coordinates)}"
    )

    print()

    if errors:
        print("First 10 field errors:")
        for error in errors[:10]:
            print("-", error)

    print()

    if (
        not errors
        and not duplicate_ids
        and not invalid_coordinates
    ):
        print("VALIDATION RESULT: PASSED")
    else:
        print("VALIDATION RESULT: FAILED")


if __name__ == "__main__":
    main()