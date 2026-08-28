import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


QUERY = """
WITH selected_route AS (
    SELECT
        id,
        geometry,
        ST_Length(geometry::geography) / 1000.0
            AS route_length_km
    FROM routes
    ORDER BY id DESC
    LIMIT 1
),

candidates AS (
    SELECT
        c.id,
        c.charger_id,
        c.name,
        c.city,
        c.state,
        c.latitude,
        c.longitude,
        c.location,

        r.geometry AS route_geometry,
        r.route_length_km

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

    ROUND(
        (
            ST_Distance(
                location,
                route_geometry::geography
            ) / 1000
        )::numeric,
        2
    ) AS distance_from_route_km,

    ROUND(
        (
            ST_LineLocatePoint(
                route_geometry,
                location::geometry
            ) * route_length_km
        )::numeric,
        2
    ) AS route_progress_km,

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
    ) AS route_point_lat

FROM candidates

ORDER BY route_progress_km;
"""


def get_route_candidates() -> list[dict]:
    connection = psycopg2.connect(**DB_CONFIG)

    try:
        with connection.cursor() as cursor:
            cursor.execute(QUERY)

            rows = cursor.fetchall()

            candidates = []

            for row in rows:

                (
                    charger_id,
                    name,
                    city,
                    state,
                    latitude,
                    longitude,
                    distance_from_route_km,
                    route_progress_km,
                    route_point_lon,
                    route_point_lat,
                ) = row

                candidates.append(
                    {
                        "charger_id": charger_id,
                        "name": name,
                        "city": city,
                        "state": state,
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                        "distance_from_route_km": float(
                            distance_from_route_km
                        ),
                        "route_progress_km": float(
                            route_progress_km
                        ),
                        "route_point_lon": float(
                            route_point_lon
                        ),
                        "route_point_lat": float(
                            route_point_lat
                        ),
                    }
                )

            return candidates

    finally:
        connection.close()


if __name__ == "__main__":

    candidates = get_route_candidates()

    print("DATABASE ROUTE CANDIDATES")
    print("=" * 110)

    print(
        f"Candidates found: {len(candidates)}"
    )

    print()

    for candidate in candidates:

        print(
            f"{candidate['charger_id']} | "
            f"{candidate['name']} | "
            f"route progress: "
            f"{candidate['route_progress_km']:.2f} km | "
            f"from route: "
            f"{candidate['distance_from_route_km']:.2f} km"
        )