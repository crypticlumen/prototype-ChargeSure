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

# Current demo trip:
# Ahmedabad → Vadodara
ORIGIN_LAT = 23.0225
ORIGIN_LON = 72.5714

# Current 2W demo profile
BATTERY_PERCENT = 42.0
BATTERY_CAPACITY_KWH = 3.2
EFFICIENCY_WH_PER_KM = 45.0

SAFETY_RESERVE_PERCENT = 20.0


def calculate_safe_range():
    available_energy_kwh = (
        BATTERY_CAPACITY_KWH
        * BATTERY_PERCENT
        / 100
    )

    available_energy_wh = (
        available_energy_kwh * 1000
    )

    estimated_range_km = (
        available_energy_wh
        / EFFICIENCY_WH_PER_KM
    )

    safe_range_km = (
        estimated_range_km
        * (1 - SAFETY_RESERVE_PERCENT / 100)
    )

    return (
    available_energy_kwh,
    estimated_range_km,
    safe_range_km,
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

        ST_LineLocatePoint(
            route_geometry,
            location::geometry
        ) * route_length_km
        AS route_progress_km

    FROM (
        SELECT
            c.*,
            chargers.location
        FROM candidates c
        JOIN chargers
            ON chargers.charger_id = c.charger_id
    ) x

    ORDER BY route_progress_km;
    """

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    finally:
        connection.close()


def get_access_distance(route_lon, route_lat, charger_lon, charger_lat):

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
        return None

    distance = data["distances"][0][1]

    if distance is None:
        return None

    return distance / 1000


def main():

    _, estimated_range, safe_range = (
        calculate_safe_range()
    )

    candidates = get_candidates()

    print("CHARGER RANGE SAFETY")
    print("=" * 120)

    print(
        f"Estimated range: {estimated_range:.2f} km"
    )

    print(
        f"Safe range:      {safe_range:.2f} km"
    )

    print("=" * 120)

    for row in candidates:

        (
            charger_id,
            name,
            city,
            state,
            charger_lat,
            charger_lon,
            route_progress_km,
        ) = row

        route_progress_km = float(
            route_progress_km
        )

        # Find the nearest route point.
        # We'll use PostGIS again for its coordinates.
        query = """
        SELECT
            ST_X(
                ST_ClosestPoint(
                    r.geometry,
                    c.location::geometry
                )
            ),
            ST_Y(
                ST_ClosestPoint(
                    r.geometry,
                    c.location::geometry
                )
            )
        FROM routes r
        JOIN chargers c
            ON c.charger_id = %s
        ORDER BY r.id DESC
        LIMIT 1;
        """

        connection = psycopg2.connect(
            **DB_CONFIG
        )

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    query,
                    (charger_id,)
                )

                point = cursor.fetchone()

        finally:
            connection.close()

        if not point:
            continue

        route_point_lon, route_point_lat = point

        access_distance = get_access_distance(
            route_point_lon,
            route_point_lat,
            charger_lon,
            charger_lat,
        )

        if access_distance is None:
            print(
                f"{charger_id} | "
                f"{name} | "
                f"ACCESS UNAVAILABLE"
            )
            continue

        required_distance = (
            route_progress_km
            + access_distance
        )

        range_safe = (
            required_distance <= safe_range
        )

        status = (
            "SAFE"
            if range_safe
            else "UNSAFE"
        )

        print(
            f"{charger_id} | "
            f"{name} | "
            f"progress: {route_progress_km:.2f} km | "
            f"access: {access_distance:.2f} km | "
            f"required: {required_distance:.2f} km | "
            f"{status}"
        )


if __name__ == "__main__":
    main()