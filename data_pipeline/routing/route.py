import json

import requests
import psycopg2


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


def get_route(start_lon, start_lat, end_lon, end_lat):
    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};"
        f"{end_lon},{end_lat}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"Routing failed: {data.get('code')}"
        )

    route = data["routes"][0]

    return {
        "distance_km": route["distance"] / 1000,
        "duration_minutes": route["duration"] / 60,
        "geometry": route["geometry"],
    }

def get_road_distances(
    origin_lon,
    origin_lat,
    destinations,
):
    """
    Calculate road-network distances from one origin
    to multiple destination coordinates.

    destinations:
        [
            {
                "id": "...",
                "lon": ...,
                "lat": ...
            }
        ]
    """

    if not destinations:
        return []

    origin = f"{origin_lon},{origin_lat}"

    destination_string = ";".join(
        f"{item['lon']},{item['lat']}"
        for item in destinations
    )

    coordinates = (
        f"{origin};{destination_string}"
    )

    url = (
        f"{OSRM_URL.replace('/route/v1/driving', '')}"
        f"/table/v1/driving/{coordinates}"
    )

    params = {
        "annotations": "distance,duration",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM table failed: {data.get('code')}"
        )

    # First row represents the origin.
    origin_distances = data["distances"][0]
    origin_durations = data["durations"][0]

    results = []

    for index, destination in enumerate(destinations):
        matrix_index = index + 1

        distance_m = origin_distances[matrix_index]
        duration_s = origin_durations[matrix_index]

        results.append(
            {
                "id": destination["id"],
                "distance_km": (
                    distance_m / 1000
                    if distance_m is not None
                    else None
                ),
                "duration_minutes": (
                    duration_s / 60
                    if duration_s is not None
                    else None
                ),
            }
        )

def get_road_distances(
    origin_lon,
    origin_lat,
    destinations,
):
    """
    Calculate road-network distances from one origin
    to multiple destination coordinates.

    destinations:
        [
            {
                "id": "...",
                "lon": ...,
                "lat": ...
            }
        ]
    """

    if not destinations:
        return []

    origin = f"{origin_lon},{origin_lat}"

    destination_string = ";".join(
        f"{item['lon']},{item['lat']}"
        for item in destinations
    )

    coordinates = (
        f"{origin};{destination_string}"
    )

    url = (
        f"{OSRM_URL.replace('/route/v1/driving', '')}"
        f"/table/v1/driving/{coordinates}"
    )

    params = {
        "annotations": "distance,duration",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM table failed: {data.get('code')}"
        )

    # First row represents the origin.
    origin_distances = data["distances"][0]
    origin_durations = data["durations"][0]

    results = []

    for index, destination in enumerate(destinations):
        matrix_index = index + 1

        distance_m = origin_distances[matrix_index]
        duration_s = origin_durations[matrix_index]

        results.append(
            {
                "id": destination["id"],
                "distance_km": (
                    distance_m / 1000
                    if distance_m is not None
                    else None
                ),
                "duration_minutes": (
                    duration_s / 60
                    if duration_s is not None
                    else None
                ),
            }
        )

    
def get_road_distances(
    origin_lon,
    origin_lat,
    destinations,
):
    """
    Calculate road-network distances from one origin
    to multiple destination coordinates.

    destinations:
        [
            {
                "id": "...",
                "lon": ...,
                "lat": ...
            }
        ]
    """

    if not destinations:
        return []

    origin = f"{origin_lon},{origin_lat}"

    destination_string = ";".join(
        f"{item['lon']},{item['lat']}"
        for item in destinations
    )

    coordinates = (
        f"{origin};{destination_string}"
    )

    url = (
        f"{OSRM_URL.replace('/route/v1/driving', '')}"
        f"/table/v1/driving/{coordinates}"
    )

    params = {
        "annotations": "distance,duration",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM table failed: {data.get('code')}"
        )

    # First row represents the origin.
    origin_distances = data["distances"][0]
    origin_durations = data["durations"][0]

    results = []

    for index, destination in enumerate(destinations):
        matrix_index = index + 1

        distance_m = origin_distances[matrix_index]
        duration_s = origin_durations[matrix_index]

        results.append(
            {
                "id": destination["id"],
                "distance_km": (
                    distance_m / 1000
                    if distance_m is not None
                    else None
                ),
                "duration_minutes": (
                    duration_s / 60
                    if duration_s is not None
                    else None
                ),
            }
        )

    return results



def save_route(
    start_lat,
    start_lon,
    end_lat,
    end_lon,
    route,
):
    connection = psycopg2.connect(**DB_CONFIG)

    try:
        cursor = connection.cursor()

        geometry_json = json.dumps(route["geometry"])

        query = """
            INSERT INTO routes (
                start_lat,
                start_lon,
                end_lat,
                end_lon,
                distance_km,
                duration_minutes,
                geometry
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                ST_SetSRID(
                    ST_GeomFromGeoJSON(%s),
                    4326
                )
            )
            RETURNING id;
        """

        cursor.execute(
            query,
            (
                start_lat,
                start_lon,
                end_lat,
                end_lon,
                route["distance_km"],
                route["duration_minutes"],
                geometry_json,
            ),
        )

        route_id = cursor.fetchone()[0]

        connection.commit()

        return route_id

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":

    # Ahmedabad → Vadodara
    start_lon = 72.5714
    start_lat = 23.0225

    end_lon = 73.1812
    end_lat = 22.3072

    print("Requesting route...")

    route = get_route(
        start_lon,
        start_lat,
        end_lon,
        end_lat,
    )

    print()
    print("ROUTE RESULT")
    print("=" * 50)
    print(
        f"Distance: "
        f"{route['distance_km']:.2f} km"
    )
    print(
        f"Duration: "
        f"{route['duration_minutes']:.2f} minutes"
    )
    print(
        f"Geometry points: "
        f"{len(route['geometry']['coordinates'])}"
    )

    route_id = save_route(
        start_lat,
        start_lon,
        end_lat,
        end_lon,
        route,
    )

    print()
    print("DATABASE")
    print("=" * 50)
    print(f"Route saved with ID: {route_id}")


    