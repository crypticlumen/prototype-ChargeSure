import psycopg2
import requests


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}

OSRM_TABLE_URL = (
    "https://router.project-osrm.org/table/v1/driving"
)


def get_candidates():

    query = """
    WITH selected_route AS (
        SELECT
            geometry
        FROM routes
        ORDER BY id DESC
        LIMIT 1
    ),

    candidates AS (
        SELECT
            c.charger_id,
            c.name,
            c.city,
            c.state,
            c.latitude,
            c.longitude,
            c.location,
            r.geometry AS route_geometry,
            ST_Length(
                r.geometry::geography
            ) / 1000.0 AS route_length_km
        FROM chargers c
        CROSS JOIN selected_route r
        WHERE ST_DWithin(
            c.location,
            r.geometry::geography,
            5000
        )
    )

    SELECT
        charger_id,
        name,
        city,
        state,
        latitude,
        longitude,

        ST_X(
            ST_ClosestPoint(
                route_geometry,
                location::geometry
            )
        ) AS route_point_lon,

        ST_Y(
            ST_ClosestPoint(
                route_geometry,
                location::geometry
            )
        ) AS route_point_lat,

        ST_LineLocatePoint(
            route_geometry,
            location::geometry
        ) * route_length_km
        AS route_progress_km

    FROM candidates

    ORDER BY route_progress_km;
    """

    conn = psycopg2.connect(**DB_CONFIG)

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            rows = cursor.fetchall()

            return rows

    finally:
        conn.close()


def calculate_access_distances(rows):

    if not rows:
        return []

    destinations = []

    for row in rows:

        (
            charger_id,
            name,
            city,
            state,
            charger_lat,
            charger_lon,
            route_point_lon,
            route_point_lat,
            route_progress_km,
        ) = row

        destinations.append(
            {
                "charger_id": charger_id,
                "name": name,
                "city": city,
                "state": state,
                "charger_lat": charger_lat,
                "charger_lon": charger_lon,
                "route_point_lon": route_point_lon,
                "route_point_lat": route_point_lat,
                "route_progress_km": float(
                    route_progress_km
                ),
            }
        )

    results = []

    for item in destinations:

        origin = (
            f"{item['route_point_lon']},"
            f"{item['route_point_lat']}"
        )

        destination = (
            f"{item['charger_lon']},"
            f"{item['charger_lat']}"
        )

        coordinates = (
            f"{origin};{destination}"
        )

        url = (
            f"{OSRM_TABLE_URL}/"
            f"{coordinates}"
        )

        params = {
            "annotations": "distance,duration"
        }

        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("code") != "Ok":
            continue

        distance = data["distances"][0][1]
        duration = data["durations"][0][1]

        item["road_access_km"] = (
            distance / 1000
            if distance is not None
            else None
        )

        item["road_access_minutes"] = (
            duration / 60
            if duration is not None
            else None
        )

        results.append(item)

    return results


def main():

    rows = get_candidates()

    results = calculate_access_distances(rows)

    print("CHARGER ACCESS ANALYSIS")
    print("=" * 120)

    for item in results:

        print(
            f"{item['charger_id']} | "
            f"{item['name']} | "
            f"progress: "
            f"{item['route_progress_km']:.2f} km | "
            f"road access: "
            f"{item['road_access_km']:.2f} km | "
            f"access time: "
            f"{item['road_access_minutes']:.2f} min"
        )


if __name__ == "__main__":
    main()