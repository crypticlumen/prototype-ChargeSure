import json
from pathlib import Path


FILE = Path("data/processed/chargers_normalized.json")

SUSPICIOUS = {
    "Ahmedabad",
    "Burari",
}


def main():

    with FILE.open("r", encoding="utf-8") as file:
        chargers = json.load(file)

    print("Suspicious state records")
    print("=" * 60)

    for charger in chargers:

        state = charger.get("state")

        if state in SUSPICIOUS:

            print(
                f"\nID:      {charger['charger_id']}"
            )

            print(
                f"Name:    {charger['name']}"
            )

            print(
                f"City:    {charger['city']}"
            )

            print(
                f"State:   {charger['state']}"
            )

            print(
                f"Address: {charger['address']}"
            )

            print(
                f"Lat/Lon: "
                f"{charger['latitude']}, "
                f"{charger['longitude']}"
            )


if __name__ == "__main__":
    main()