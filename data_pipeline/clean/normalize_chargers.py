import json
import re
from pathlib import Path


INPUT_FILE = Path("data/processed/chargers_clean.json")
OUTPUT_FILE = Path("data/processed/chargers_normalized.json")


# ---------------------------------------------------------
# State normalization
# ---------------------------------------------------------

STATE_CORRECTIONS = {
    "maharshtra": "Maharashtra",
    "mahrashtra": "Maharashtra",
    "west bengal": "West Bengal",
    "tamilnadu": "Tamil Nadu",
}


VALID_STATES = {
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Puducherry",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def clean_spaces(text: str | None) -> str | None:
    if not text:
        return None

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",\s*,+", ", ", text)

    return text.strip(" ,")


def normalize_state(state: str | None) -> str | None:
    if not state:
        return None

    state = clean_spaces(state)

    if not state:
        return None

    # Direct correction
    corrected = STATE_CORRECTIONS.get(state.lower())

    if corrected:
        return corrected

    # Case normalization
    for valid_state in VALID_STATES:
        if state.lower() == valid_state.lower():
            return valid_state

    # Keep unknown values for investigation.
    return state


def extract_city_from_address(
    address: str | None,
) -> str | None:

    if not address:
        return None

    address = clean_spaces(address)

    if not address:
        return None

    # Common Indian postal-code pattern:
    # "Ahmedabad, Gujarat 380026"
    match = re.search(
        r",\s*([^,]+),\s*[A-Za-z .]+(?:\s+\d{6})?$",
        address,
    )

    if match:
        candidate = clean_spaces(match.group(1))

        if candidate:
            return candidate

    # Look for common "near <city>" style.
    match = re.search(
        r"\b(?:near|at|in)\s+([A-Za-z .-]+)",
        address,
        flags=re.IGNORECASE,
    )

    if match:
        candidate = clean_spaces(match.group(1))

        if candidate:
            return candidate

    return None


def normalize_charger(charger: dict) -> dict:

    normalized = charger.copy()

    normalized["state"] = normalize_state(
        charger.get("state")
    )

    normalized["address"] = clean_spaces(
        charger.get("address")
    )

    normalized["name"] = clean_spaces(
        charger.get("name")
    )

        # Confirmed source-data corrections
    if charger.get("charger_id") == "OCM-502323":
        normalized["state"] = "Gujarat"

    elif charger.get("charger_id") == "OCM-502306":
        normalized["state"] = "Gujarat"

    elif charger.get("charger_id") == "OCM-496646":
        normalized["state"] = "Delhi"

    # Only attempt city derivation when city is missing.
    if not charger.get("city"):
        derived_city = extract_city_from_address(
            charger.get("address")
        )

        if derived_city:
            normalized["city"] = derived_city

    return normalized


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        chargers = json.load(file)

    normalized = []

    city_recovered = 0
    city_still_missing = 0

    state_corrected = 0

    for charger in chargers:

        original_city = charger.get("city")
        original_state = charger.get("state")

        result = normalize_charger(charger)

        if (
            not original_city
            and result.get("city")
        ):
            city_recovered += 1

        if not result.get("city"):
            city_still_missing += 1

        if (
            original_state
            and result.get("state")
            and original_state != result["state"]
        ):
            state_corrected += 1

        normalized.append(result)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            normalized,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("NORMALIZATION COMPLETE")
    print("=" * 50)

    print(
        f"Input records:          {len(chargers)}"
    )

    print(
        f"City values recovered:  {city_recovered}"
    )

    print(
        f"City still missing:     {city_still_missing}"
    )

    print(
        f"State values corrected: {state_corrected}"
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()