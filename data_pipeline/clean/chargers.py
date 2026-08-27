import json
from pathlib import Path
from typing import Any


RAW_DIR = Path("data/raw/openchargemap")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_latest_raw_file() -> Path:
    files = sorted(
        RAW_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            f"No JSON files found in {RAW_DIR}"
        )

    return files[0]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def clean_number(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_address(address_info: dict) -> str | None:
    parts = [
        clean_text(address_info.get("AddressLine1")),
        clean_text(address_info.get("AddressLine2")),
    ]

    parts = [part for part in parts if part]

    return ", ".join(parts) if parts else None


def normalize_charger(record: dict) -> dict:
    address_info = record.get("AddressInfo") or {}
    connections = record.get("Connections") or []

    latitude = clean_number(address_info.get("Latitude"))
    longitude = clean_number(address_info.get("Longitude"))

    power_values = []

    for connection in connections:
        power = clean_number(connection.get("PowerKW"))

        if power is not None and power > 0:
            power_values.append(power)

    max_power_kw = max(power_values) if power_values else None

    charger_id = f"OCM-{record.get('ID')}"

    return {
        "charger_id": charger_id,
        "source": "openchargemap",
        "source_id": str(record.get("ID"))
        if record.get("ID")
        else None,

        "name": clean_text(address_info.get("Title")),

        # OperatorID is not a human-readable operator name.
        "operator": None,

        "address": build_address(address_info),

        "city": clean_text(address_info.get("Town")),
        "state": clean_text(address_info.get("StateOrProvince")),
        "country": "India",

        "latitude": latitude,
        "longitude": longitude,

        "power_kw": max_power_kw,

        "number_of_points": record.get("NumberOfPoints"),

        # Status will be mapped separately after verification.
        "status": "unknown",

        "last_verified_at": record.get("DateLastVerified"),
    }


def main():
    raw_file = find_latest_raw_file()

    print(f"Reading: {raw_file}")

    with raw_file.open("r", encoding="utf-8") as file:
        records = json.load(file)

    cleaned = []

    for record in records:
        try:
            charger = normalize_charger(record)

            lat = charger["latitude"]
            lon = charger["longitude"]

            # Reject missing coordinates.
            if lat is None or lon is None:
                continue

            # Validate coordinates.
            if not (-90 <= lat <= 90):
                continue

            if not (-180 <= lon <= 180):
                continue

            cleaned.append(charger)

        except Exception as exc:
            print(
                f"Skipping invalid record "
                f"{record.get('ID')}: {exc}"
            )

    output_file = OUTPUT_DIR / "chargers_clean.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            cleaned,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"Raw records:     {len(records)}")
    print(f"Clean records:   {len(cleaned)}")
    print(f"Removed records: {len(records) - len(cleaned)}")
    print(f"Output:          {output_file}")


if __name__ == "__main__":
    main()