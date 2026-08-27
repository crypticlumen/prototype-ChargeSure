import json
from pathlib import Path

import psycopg2


INPUT_FILE = Path(
    "data/processed/chargers_normalized.json"
)


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


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

    print(
        f"Loading {len(chargers)} chargers..."
    )

    conn = psycopg2.connect(**DB_CONFIG)

    try:

        with conn.cursor() as cur:

            inserted = 0
            skipped = 0

            for charger in chargers:

                charger_id = charger["charger_id"]

                # Prevent duplicate insertion.
                cur.execute(
                    """
                    SELECT 1
                    FROM chargers
                    WHERE charger_id = %s
                    """,
                    (charger_id,)
                )

                if cur.fetchone():
                    skipped += 1
                    continue

                cur.execute(
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
                    VALUES (
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
                        charger.get(
                            "number_of_points"
                        ),
                        charger["status"],
                        charger["last_verified_at"],
                    )
                )

                inserted += 1

            conn.commit()

            print()
            print("LOAD COMPLETE")
            print("=" * 50)
            print(f"Inserted: {inserted}")
            print(f"Skipped:  {skipped}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()