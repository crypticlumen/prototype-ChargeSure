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
        geometry,
        ST_Length(geometry::geography) / 1000.0
            AS route_length_km
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
        c.location,
        r.geometry,
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

    ROUND(
        (
            ST_Distance(
                location,
                geometry::geography
            ) / 1000
        )::numeric,
        2
    ) AS distance_from_route_km,

    ROUND(
        (
            ST_LineLocatePoint(
                geometry,
                location::geometry
            ) * route_length_km
        )::numeric,
        2
    ) AS route_progress_km,

    ROUND(
        route_length_km::numeric,
        2
    ) AS total_route_length_km

FROM candidates

ORDER BY route_progress_km;
"""


def main():

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        with connection.cursor() as cursor:

            cursor.execute(QUERY)

            rows = cursor.fetchall()

            print("ROUTE PROGRESS")
            print("=" * 110)

            for row in rows:

                (
                    charger_id,
                    name,
                    city,
                    state,
                    distance_from_route,
                    route_progress,
                    route_length,
                ) = row

                print(
                    f"{charger_id} | "
                    f"{name} | "
                    f"route distance: "
                    f"{distance_from_route:.2f} km | "
                    f"progress: "
                    f"{route_progress:.2f} km | "
                    f"route total: "
                    f"{route_length:.2f} km"
                )

    finally:
        connection.close()


if __name__ == "__main__":
    main()