import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests


OUTPUT_DIR = Path("data/raw/openchargemap")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("OPENCHARGEMAP_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "OPENCHARGEMAP_API_KEY environment variable is not set."
    )


def fetch_chargers():
    url = "https://api.openchargemap.io/v3/poi/"

    params = {
        "key": API_KEY,
        "countrycode": "IN",
        "maxresults": 500,
        "compact": "true",
        "verbose": "false",
    }

    print("Fetching charger data from OpenChargeMap...")

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    output_file = (
        OUTPUT_DIR /
        f"chargers_india_{timestamp}.json"
    )

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Fetched records: {len(data)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    fetch_chargers()