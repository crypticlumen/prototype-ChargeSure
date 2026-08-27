import json
from pathlib import Path
from collections import Counter


INPUT_FILE = Path("data/processed/chargers_clean.json")


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        chargers = json.load(file)

    print(f"Total chargers: {len(chargers)}")
    print("=" * 60)

    # ----------------------------
    # Missing city
    # ----------------------------

    missing_city = [
        charger
        for charger in chargers
        if not charger.get("city")
    ]

    print(f"\nMissing city: {len(missing_city)}")

    print("\nSample records with missing city:")

    for charger in missing_city[:10]:
        print(
            f"- {charger['charger_id']} | "
            f"{charger['name']} | "
            f"{charger['address']} | "
            f"{charger['state']}"
        )

    # ----------------------------
    # Missing state
    # ----------------------------

    missing_state = [
        charger
        for charger in chargers
        if not charger.get("state")
    ]

    print(f"\nMissing state: {len(missing_state)}")

    for charger in missing_state[:10]:
        print(
            f"- {charger['charger_id']} | "
            f"{charger['name']} | "
            f"{charger['address']} | "
            f"{charger['city']}"
        )

    # ----------------------------
    # State values
    # ----------------------------

    states = Counter(
        charger.get("state")
        for charger in chargers
        if charger.get("state")
    )

    print("\nAll state values:")
    for state, count in states.most_common():
        print(f"{repr(state)} : {count}")

    # ----------------------------
    # Missing power
    # ----------------------------

    missing_power = [
        charger
        for charger in chargers
        if charger.get("power_kw") is None
    ]

    print(f"\nMissing power: {len(missing_power)}")

    for charger in missing_power[:10]:
        print(
            f"- {charger['charger_id']} | "
            f"{charger['name']} | "
            f"{charger['city']} | "
            f"{charger['state']}"
        )


if __name__ == "__main__":
    main()