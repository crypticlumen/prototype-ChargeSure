import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


INPUT_FILE = Path(
    "data/processed/chargers_normalized.json"
)


def get_database_url() -> str:
    """Return the PostgreSQL connection URL from DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    return database_url


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        chargers = json.load(file)

    print(f"Loading {len(chargers)} chargers...")

    database_url = get_database_url()

    conn = psycopg2.connect(
        database_url,
        connect_timeout=20,
    )

    try:
        rows = []

        for charger in chargers:
            rows.append(
                (
                    charger["charger_id"],
                    charger["source"],
                    charger["source_id"],
                    charger["name"],
                    charger["operator"],
                    charger["address"],
                    charger["city"],
                    charger["state"],
                    charger["country"],
                    charger["latitude"],
                    charger["longitude"],
                    charger["longitude"],
                    charger["latitude"],
                    charger["power_kw"],
                    charger.get("number_of_points"),
                    charger["status"],
                    charger["last_verified_at"],
                )
            )

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO chargers (
                    charger_id,
                    source,
                    source_id,
                    name,
                    operator,
                    address,
                    city,
                    state,
                    country,
                    latitude,
                    longitude,
                    location,
                    power_kw,
                    number_of_points,
                    status,
                    last_verified_at
                )
                VALUES %s
                ON CONFLICT (charger_id) DO NOTHING
                """,
                rows,
                template="""
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    ST_SetSRID(
                        ST_MakePoint(%s, %s),
                        4326
                    )::geography,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                page_size=500,
            )

            inserted = cur.rowcount

        conn.commit()

        skipped = len(chargers) - inserted

        print()
        print("LOAD COMPLETE")
        print("=" * 50)
        print(f"Total records: {len(chargers)}")
        print(f"Inserted:      {inserted}")
        print(f"Skipped:       {skipped}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()