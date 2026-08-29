import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


def get_route_candidates():
    connection = psycopg2.connect(**DB_CONFIG)

    query = """
        WITH selected_route AS (
            SELECT
                id,
                geometry
            FROM routes
            ORDER BY id DESC
            LIMIT 1
        )
        SELECT
            c.charger_id,
            c.name,
            c.city,
            c.state,
            c.latitude,
            c.longitude,

            ROUND(
                (
                    ST_Distance(
                        c.location,
                        r.geometry
                    ) / 1000
                )::numeric,
                2
            ) AS distance_from_route_km

        FROM chargers c

        CROSS JOIN selected_route r

        WHERE ST_DWithin(
            c.location,
            r.geometry,
            5000
        )

        ORDER BY distance_from_route_km;
    """

    try:
        with connection.cursor() as cursor:

            cursor.execute(query)

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
                ) = row

                candidates.append(
                    {
                        "charger_id": charger_id,
                        "name": name,
                        "city": city,
                        "state": state,
                        "latitude": latitude,
                        "longitude": longitude,
                        "distance_from_route_km": float(
                            distance_from_route_km
                        ),
                    }
                )

            return candidates

    finally:
        connection.close()


if __name__ == "__main__":

    candidates = get_route_candidates()

    print(
        f"Route candidates: {len(candidates)}"
    )

    print("=" * 70)

    for candidate in candidates:
        print(
            f"{candidate['charger_id']} | "
            f"{candidate['name']} | "
            f"{candidate['distance_from_route_km']} km"
        )