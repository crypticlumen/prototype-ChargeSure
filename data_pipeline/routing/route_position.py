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
        geometry
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
        c.location,
        r.geometry AS route_geometry
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
                route_geometry::geography
            ) / 1000
        )::numeric,
        2
    ) AS distance_from_route_km,

    ST_AsText(
        ST_ClosestPoint(
            route_geometry,
            location::geometry
        )
    ) AS nearest_route_point

FROM candidates

ORDER BY distance_from_route_km;
"""


def main():

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        with connection.cursor() as cursor:

            cursor.execute(QUERY)

            rows = cursor.fetchall()

            print("ROUTE POSITION RESULTS")
            print("=" * 100)

            for row in rows:

                (
                    charger_id,
                    name,
                    city,
                    state,
                    distance_from_route,
                    nearest_point,
                ) = row

                print(
                    f"{charger_id} | "
                    f"{name} | "
                    f"route-distance: "
                    f"{distance_from_route} km | "
                    f"nearest route point: "
                    f"{nearest_point}"
                )

    finally:
        connection.close()


if __name__ == "__main__":
    main()