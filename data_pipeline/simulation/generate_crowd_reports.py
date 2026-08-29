import random
from datetime import datetime, timedelta, timezone

import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


CHARGER_COUNT = 500
DAYS_OF_HISTORY = 90
RANDOM_SEED = 43


def get_chargers():
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, charger_id
                FROM chargers
                ORDER BY id
                LIMIT %s
                """,
                (CHARGER_COUNT,),
            )

            return cur.fetchall()

    finally:
        conn.close()


def generate_hidden_profile():
    """
    Hidden synthetic behavior used ONLY to generate observations.

    This value must NEVER be used as an ML feature.
    """

    roll = random.random()

    if roll < 0.20:
        return random.uniform(0.45, 0.65)

    if roll < 0.70:
        return random.uniform(0.65, 0.85)

    return random.uniform(0.85, 0.97)


def main():

    random.seed(RANDOM_SEED)

    chargers = get_chargers()

    if not chargers:
        raise RuntimeError(
            "No chargers found."
        )

    charger_ids = [
        charger[0]
        for charger in chargers
    ]

    print(
        f"Selected {len(chargers)} chargers."
    )

    conn = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with conn.cursor() as cur:

            # Remove only synthetic crowd reports.
            # Any future real data remains untouched.
            cur.execute(
                """
                DELETE FROM crowd_reports
                WHERE charger_id = ANY(%s)
                  AND source = 'simulated'
                """,
                (charger_ids,),
            )

            start = (
                datetime.now(timezone.utc)
                - timedelta(
                    days=DAYS_OF_HISTORY
                )
            )

            total_reports = 0

            for index, (
                internal_id,
                charger_id,
            ) in enumerate(chargers):

                reliability = (
                    generate_hidden_profile()
                )

                # More active chargers receive
                # more crowd observations.
                report_count = random.randint(
                    15,
                    40,
                )

                for _ in range(report_count):

                    reported_at = (
                        start
                        + timedelta(
                            days=random.randint(
                                0,
                                DAYS_OF_HISTORY - 1,
                            ),
                            minutes=random.randint(
                                0,
                                1439,
                            ),
                        )
                    )

                    if random.random() < reliability:

                        reported_status = random.choice(
                            [
                                "available",
                                "occupied",
                            ]
                        )

                        trust_score = random.uniform(
                            70,
                            100,
                        )

                    else:

                        reported_status = random.choice(
                            [
                                "faulted",
                                "offline",
                            ]
                        )

                        trust_score = random.uniform(
                            40,
                            90,
                        )

                    cur.execute(
                        """
                        INSERT INTO crowd_reports (
                            charger_id,
                            reported_at,
                            reported_status,
                            user_trust_score,
                            source
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            internal_id,
                            reported_at,
                            reported_status,
                            round(
                                trust_score,
                                2,
                            ),
                            "simulated",
                        ),
                    )

                    total_reports += 1

                if (
                    index + 1
                ) % 50 == 0:

                    print(
                        f"Processed "
                        f"{index + 1}/"
                        f"{len(chargers)} chargers..."
                    )

            conn.commit()

        print()
        print("CROWD SIMULATION COMPLETE")
        print("=" * 60)
        print(
            f"Chargers simulated: "
            f"{len(chargers)}"
        )
        print(
            f"History duration: "
            f"{DAYS_OF_HISTORY} days"
        )
        print(
            f"Crowd reports generated: "
            f"{total_reports}"
        )
        print(
            "Data source: simulated"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()