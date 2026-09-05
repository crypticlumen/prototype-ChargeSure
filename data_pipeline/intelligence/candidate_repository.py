import json

import psycopg2

from app.config import get_settings


settings = get_settings()


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
            NULLIF(TRIM(ct.normalized_type), ''),
            NULLIF(TRIM(cc.connector_type), ''),
            'unknown'
        )
        ORDER BY COALESCE(
            NULLIF(TRIM(ct.normalized_type), ''),
            NULLIF(TRIM(cc.connector_type), ''),
            'unknown'
        )
    ) AS connector_types,

    MAX(cc.power_kw) AS max_power_kw,

    CASE

        /* ---------------------------------------------------------
           1. Direct verified match
           --------------------------------------------------------- */
        WHEN EXISTS (
            SELECT 1
            FROM charger_connectors cc2
            LEFT JOIN connector_types ct2
                ON LOWER(TRIM(ct2.raw_connector_type))
                 = LOWER(TRIM(cc2.connector_type))

            WHERE cc2.charger_id = c.id
              AND ct2.verified = TRUE
              AND (
                    LOWER(TRIM(ct2.normalized_type))
                        = LOWER(TRIM(%s))

                    OR (
                        LOWER(TRIM(%s)) IN (
                            'ccs',
                            'ccs2',
                            'ccs combo 2',
                            'combo 2',
                            'ccs combo'
                        )
                        AND LOWER(TRIM(ct2.normalized_type)) IN (
                            'ccs',
                            'ccs2',
                            'ccs combo 2',
                            'combo 2',
                            'ccs combo'
                        )
                    )

                    OR (
                        LOWER(TRIM(%s)) IN (
                            'type2',
                            'type 2',
                            'ac type 2'
                        )
                        AND LOWER(TRIM(ct2.normalized_type)) IN (
                            'type2',
                            'type 2',
                            'ac type 2'
                        )
                    )

                    OR (
                        LOWER(TRIM(%s)) IN (
                            'gbt',
                            'gb/t',
                            'gb t',
                            'gbt dc'
                        )
                        AND LOWER(TRIM(ct2.normalized_type)) IN (
                            'gbt',
                            'gb/t',
                            'gb t',
                            'gbt dc'
                        )
                    )

                    OR (
                        LOWER(TRIM(%s)) IN (
                            'chademo',
                            'cha de mo'
                        )
                        AND LOWER(TRIM(ct2.normalized_type)) IN (
                            'chademo',
                            'cha de mo'
                        )
              )
        )
        THEN 'COMPATIBLE'


        /* ---------------------------------------------------------
           2. Unknown information exists
           --------------------------------------------------------- */
        WHEN EXISTS (
            SELECT 1
            FROM charger_connectors cc3
            LEFT JOIN connector_types ct3
                ON LOWER(TRIM(ct3.raw_connector_type))
                 = LOWER(TRIM(cc3.connector_type))

            WHERE cc3.charger_id = c.id
              AND (
                    ct3.raw_connector_type IS NULL
                    OR ct3.verified = FALSE
                    OR ct3.normalized_type IS NULL
                    OR LOWER(TRIM(ct3.normalized_type)) = 'unknown'
              )
        )
        THEN 'UNKNOWN'


        /* ---------------------------------------------------------
           3. Connector data exists but does not match
           --------------------------------------------------------- */
        WHEN EXISTS (
            SELECT 1
            FROM charger_connectors cc4
            WHERE cc4.charger_id = c.id
        )
        THEN 'INCOMPATIBLE'


        /* ---------------------------------------------------------
           4. No connector rows at all
           --------------------------------------------------------- */
        ELSE 'UNKNOWN'

    END AS compatibility

FROM chargers c

LEFT JOIN charger_connectors cc
    ON cc.charger_id = c.id

LEFT JOIN connector_types ct
    ON LOWER(TRIM(ct.raw_connector_type))
     = LOWER(TRIM(cc.connector_type))

WHERE c.charger_id = %s

GROUP BY c.id;
"""


def _normalize_route_geometry(route_geometry: dict) -> dict:
    """
    Normalize common GeoJSON wrappers into a geometry object
    accepted by PostGIS ST_GeomFromGeoJSON().

    Supported:
    - LineString
    - MultiLineString
    - Feature
    - FeatureCollection
    """

    if not isinstance(route_geometry, dict):
        raise ValueError(
            "route_geometry must be a GeoJSON dictionary."
        )

    geometry_type = route_geometry.get("type")

    # Already a geometry object.
    if geometry_type in {
        "LineString",
        "MultiLineString",
    }:
        coordinates = route_geometry.get("coordinates")

        if not coordinates:
            raise ValueError(
                f"GeoJSON {geometry_type} has no coordinates."
            )

        return {
            "type": geometry_type,
            "coordinates": coordinates,
        }

    # GeoJSON Feature.
    if geometry_type == "Feature":
        geometry = route_geometry.get("geometry")

        if not isinstance(geometry, dict):
            raise ValueError(
                "GeoJSON Feature does not contain a valid geometry."
            )

        return _normalize_route_geometry(geometry)

    # GeoJSON FeatureCollection.
    if geometry_type == "FeatureCollection":
        features = route_geometry.get("features", [])

        if not features:
            raise ValueError(
                "GeoJSON FeatureCollection contains no features."
            )

        geometries = []

        for feature in features:
            if not isinstance(feature, dict):
                continue

            geometry = feature.get("geometry")

            if not isinstance(geometry, dict):
                continue

            normalized = _normalize_route_geometry(geometry)

            if normalized["type"] == "LineString":
                geometries.append(
                    normalized["coordinates"]
                )

            elif normalized["type"] == "MultiLineString":
                geometries.extend(
                    normalized["coordinates"]
                )

        if not geometries:
            raise ValueError(
                "GeoJSON FeatureCollection contains no usable "
                "LineString geometry."
            )

        if len(geometries) == 1:
            return {
                "type": "LineString",
                "coordinates": geometries[0],
            }

        return {
            "type": "MultiLineString",
            "coordinates": geometries,
        }

    raise ValueError(
        f"Unsupported route GeoJSON type: {geometry_type!r}. "
        "Expected LineString, MultiLineString, Feature, "
        "or FeatureCollection."
    )


def _clean_connector_type(value) -> str:
    """
    Normalize connector labels before returning them to the
    intelligence pipeline.
    """

    if value is None:
        return "unknown"

    value = str(value).strip()

    if not value:
        return "unknown"

    return value


def get_connector_enrichment(
    cursor,
    charger_id: str,
    vehicle_connector_type: str,
) -> dict:
    """
    Return connector information for one charger.

    Important:
    - No connector rows -> UNKNOWN.
    - Verified matching connector -> COMPATIBLE.
    - Connector rows exist but don't match -> INCOMPATIBLE.
    - Unverified/unknown connector data -> UNKNOWN.
    """

    cursor.execute(
        CONNECTOR_QUERY,
        (
            vehicle_connector_type,
            vehicle_connector_type,
            vehicle_connector_type,
            vehicle_connector_type,
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

    connector_types = [
        _clean_connector_type(value)
        for value in (row[1] or [])
        if value is not None
    ]

    # Remove duplicate unknown labels while preserving order.
    cleaned_types = []

    for connector_type in connector_types:
        if connector_type not in cleaned_types:
            cleaned_types.append(connector_type)

    return {
        "connector_types": cleaned_types,
        "max_power_kw": (
            float(row[2])
            if row[2] is not None
            else None
        ),
        "compatibility": (
            str(row[3]).upper()
            if row[3] is not None
            else "UNKNOWN"
        ),
    }


def get_route_candidates(
    route_geometry: dict,
    vehicle_connector_type: str = "CCS",
) -> list[dict]:
    """
    Get charger candidates around an OSRM route.

    The database connection is taken from ChargeSure's central
    DATABASE_URL configuration so the same code works locally
    and on Render.

    Returns:
        list[dict]
    """

    if not route_geometry:
        return []

    if not isinstance(route_geometry, dict):
        raise ValueError(
            "route_geometry must be a GeoJSON dictionary."
        )

    if not isinstance(vehicle_connector_type, str):
        raise ValueError(
            "vehicle_connector_type must be a string."
        )

    vehicle_connector_type = vehicle_connector_type.strip()

    if not vehicle_connector_type:
        raise ValueError(
            "vehicle_connector_type cannot be empty."
        )

    normalized_route_geometry = _normalize_route_geometry(
        route_geometry
    )

    # Use the same DATABASE_URL used by the FastAPI application.
    # Locally this points to the local PostgreSQL container.
    # On Render this points to the managed Render PostgreSQL instance.
    connection = psycopg2.connect(settings.database_url)

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                QUERY,
                (
                    json.dumps(
                        normalized_route_geometry
                    ),
                ),
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

                        "latitude": (
                            float(latitude)
                            if latitude is not None
                            else None
                        ),

                        "longitude": (
                            float(longitude)
                            if longitude is not None
                            else None
                        ),

                        "distance_from_route_km": (
                            float(distance_from_route_km)
                        ),

                        "route_progress_km": (
                            float(route_progress_km)
                        ),

                        "route_point_lon": (
                            float(route_point_lon)
                        ),

                        "route_point_lat": (
                            float(route_point_lat)
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