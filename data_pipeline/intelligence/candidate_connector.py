import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


def get_connector_enrichment(
    charger_id: str,
    vehicle_connector_type: str,
) -> dict:
    """
    Return connector information for a charger.

    Possible compatibility values:

        COMPATIBLE
        INCOMPATIBLE
        UNKNOWN
    """

    query = """
        SELECT
            c.charger_id,

            ARRAY_AGG(
                DISTINCT ct.normalized_type
                ORDER BY ct.normalized_type
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

        GROUP BY c.id, c.charger_id;
    """

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    vehicle_connector_type,
                    charger_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:
                return {
                    "charger_id": charger_id,
                    "connector_types": [],
                    "max_power_kw": None,
                    "compatibility": "UNKNOWN",
                }

            return {
                "charger_id": row[0],
                "connector_types": row[1] or [],
                "max_power_kw": (
                    float(row[2])
                    if row[2] is not None
                    else None
                ),
                "compatibility": row[3],
            }

    finally:
        connection.close()