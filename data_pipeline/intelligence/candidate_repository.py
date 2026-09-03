import json
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
        ST_SetSRID(
            ST_GeomFromGeoJSON(%s),
            4326
        ) AS geometry
),

route_info AS (
    SELECT
        geometry,
        ST_Length(
            geometry::geography
        ) / 1000.0 AS route_length_km
    FROM selected_route
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
    CROSS JOIN route_info r

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


CONNECTOR_QUERY = """
SELECT
    c.id,

    ARRAY_AGG(
        DISTINCT COALESCE(
            ct.normalized_type,
            'unknown'
        )
        ORDER BY COALESCE(
            ct.normalized_type,
            'unknown'
        )
    ) AS connector_types,

    MAX(cc.power_kw) AS max_power_kw,

    CASE
        WHEN EXISTS (
            SELECT 1
            FROM charger_connectors cc2
            JOIN connector_types ct2
                ON ct2.raw_connector_type =
                   cc2.connector_type
            WHERE cc2.charger_id = c.id
              AND ct2.verified = TRUE
              AND LOWER(ct2.normalized_type)
                  = LOWER(%s)
        )
        THEN 'COMPATIBLE'

        WHEN EXISTS (
            SELECT 1
            FROM charger_connectors cc3
            LEFT JOIN connector_types ct3
                ON ct3.raw_connector_type =
                   cc3.connector_type
            WHERE cc3.charger_id = c.id
              AND (
                  ct3.raw_connector_type IS NULL
                  OR ct3.verified = FALSE
                  OR ct3.normalized_type = 'unknown'
              )
        )
        THEN 'UNKNOWN'

        ELSE 'INCOMPATIBLE'
    END AS compatibility

FROM chargers c

JOIN charger_connectors cc
    ON cc.charger_id = c.id

LEFT JOIN connector_types ct
    ON ct.raw_connector_type =
       cc.connector_type

WHERE c.charger_id = %s

GROUP BY c.id;
"""


def get_connector_enrichment(
    cursor,
    charger_id: str,
    vehicle_connector_type: str,
) -> dict:

    cursor.execute(
        CONNECTOR_QUERY,
        (
            vehicle_connector_type,
            charger_id,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        return {
            "connector_types": [],
            "max_power_kw": None,
            "compatibility": "UNKNOWN",
        }

    return {
        "connector_types": row[1] or [],
        "max_power_kw": (
            float(row[2])
            if row[2] is not None
            else None
        ),
        "compatibility": row[3],
    }


def get_route_candidates(
    route_geometry: dict,
    vehicle_connector_type: str = "CCS",
) -> list[dict]:
    """
    Get charger candidates around the supplied
    current OSRM route geometry.

    No dependency on the global latest route.
    """

    if not route_geometry:
        return []

    if not vehicle_connector_type.strip():
        raise ValueError(
            "vehicle_connector_type cannot be empty."
        )

    connection = psycopg2.connect(**DB_CONFIG)

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                QUERY,
                (json.dumps(route_geometry),),
            )

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

                connector = get_connector_enrichment(
                    cursor,
                    charger_id,
                    vehicle_connector_type,
                )

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
                        "connector_types": connector[
                            "connector_types"
                        ],
                        "max_power_kw": connector[
                            "max_power_kw"
                        ],
                        "connector_compatibility": connector[
                            "compatibility"
                        ],
                    }
                )

            return candidates

    finally:
        connection.close()