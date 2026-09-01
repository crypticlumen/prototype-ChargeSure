import requests


OSRM_TABLE_URL = (
    "https://router.project-osrm.org/table/v1/driving"
)


def get_road_access_distance(
    route_lon: float,
    route_lat: float,
    charger_lon: float,
    charger_lat: float,
) -> tuple[float | None, float | None]:

    coordinates = (
        f"{route_lon},{route_lat};"
        f"{charger_lon},{charger_lat}"
    )

    url = (
        f"{OSRM_TABLE_URL}/"
        f"{coordinates}"
    )

    response = requests.get(
        url,
        params={
            "annotations": "distance,duration"
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        return None, None

    distance = data["distances"][0][1]
    duration = data["durations"][0][1]

    if distance is None:
        return None, None

    return (
        distance / 1000,
        duration / 60,
    )