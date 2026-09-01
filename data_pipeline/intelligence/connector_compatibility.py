from typing import Optional


# ---------------------------------------------------------
# ChargeSure normalized connector names
# ---------------------------------------------------------

NORMALIZED_CONNECTORS = {
    "OCM_TYPE_0": "unknown",
    "OCM_TYPE_2": "CHAdeMO",
    "OCM_TYPE_16": "J-1772",
    "OCM_TYPE_25": "Type 2",
    "OCM_TYPE_33": "CCS",
    "OCM_TYPE_35": "Type 3",
    "OCM_TYPE_1036": "Tesla",
    "OCM_TYPE_1041": "NACS",
}


def normalize_connector_type(
    connector_type: str,
) -> str:

    return NORMALIZED_CONNECTORS.get(
        connector_type,
        "unknown",
    )


def is_connector_compatible(
    charger_connector_type: str,
    vehicle_connector_type: str,
) -> bool:
    """
    Check whether a normalized charger connector
    matches the vehicle connector.

    'unknown' is NOT automatically considered compatible.
    """

    charger_type = normalize_connector_type(
        charger_connector_type
    )

    vehicle_type = vehicle_connector_type.strip()

    if (
        charger_type == "unknown"
        or vehicle_type == "unknown"
    ):
        return False

    return (
        charger_type.lower()
        == vehicle_type.lower()
    )


def get_supported_vehicle_connectors():
    return sorted(
        {
            value
            for value in NORMALIZED_CONNECTORS.values()
            if value != "unknown"
        }
    )


if __name__ == "__main__":

    print(
        "CHARGESURE CONNECTOR MAPPING"
    )

    print("=" * 60)

    for raw, normalized in (
        NORMALIZED_CONNECTORS.items()
    ):
        print(
            f"{raw:15s} → {normalized}"
        )

    print()

    print(
        "SUPPORTED VEHICLE CONNECTORS"
    )

    print("=" * 60)

    for connector in (
        get_supported_vehicle_connectors()
    ):
        print(
            f"- {connector}"
        )