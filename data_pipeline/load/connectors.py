import json
from pathlib import Path

import psycopg2


RAW_DIR = Path("data/raw/openchargemap")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


def find_latest_raw_file() -> Path:
    files = sorted(
        RAW_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError(
            f"No raw JSON files found in {RAW_DIR}"
        )

    return files[0]


def main():
    raw_file = find_latest_raw_file()

    print(f"Reading: {raw_file}")

    with raw_file.open("r", encoding="utf-8") as file:
        records = json.load(file)

    conn = psycopg2.connect(**DB_CONFIG)

    inserted = 0
    skipped = 0
    missing_chargers = 0

    try:
        with conn.cursor() as cur:

            for record in records:

                source_id = record.get("ID")

                if source_id is None:
                    continue

                charger_id = f"OCM-{source_id}"

                # Find the internal database ID.
                cur.execute(
                    """
                    SELECT id
                    FROM chargers
                    WHERE charger_id = %s
                    """,
                    (charger_id,),
                )

                row = cur.fetchone()

                if row is None:
                    missing_chargers += 1
                    continue

                internal_charger_id = row[0]

                connections = record.get("Connections") or []

                for connection in connections:

                    connector_type_id = connection.get(
                        "ConnectionTypeID"
                    )

                    power_kw = connection.get("PowerKW")
                    quantity = connection.get("Quantity") or 1

                    if connector_type_id is None:
                        continue

                    connector_type = (
                        f"OCM_TYPE_{connector_type_id}"
                    )

                    # Avoid inserting same connector twice
                    # for the same charger.
                    cur.execute(
                        """
                        SELECT 1
                        FROM charger_connectors
                        WHERE charger_id = %s
                          AND connector_type = %s
                          AND power_kw IS NOT DISTINCT FROM %s
                        """,
                        (
                            internal_charger_id,
                            connector_type,
                            power_kw,
                        ),
                    )

                    if cur.fetchone():
                        skipped += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO charger_connectors (
                            charger_id,
                            connector_type,
                            power_kw,
                            quantity
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            internal_charger_id,
                            connector_type,
                            power_kw,
                            quantity,
                        ),
                    )

                    inserted += 1

            conn.commit()

        print()
        print("CONNECTOR LOAD COMPLETE")
        print("=" * 50)
        print(f"Inserted connectors: {inserted}")
        print(f"Skipped duplicates:  {skipped}")
        print(f"Missing chargers:     {missing_chargers}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()