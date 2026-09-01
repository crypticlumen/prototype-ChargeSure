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


# -------------------------------------------
# Simulation configuration
# -------------------------------------------

TEST_CHARGER_COUNT = 500

DAYS_OF_HISTORY = 90

RANDOM_SEED = 42


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
                (TEST_CHARGER_COUNT,),
            )

            return cur.fetchall()

    finally:
        conn.close()


def generate_profile(index: int) -> float:
    """
    Assign a hidden reliability tendency for simulation.

    IMPORTANT:
    This value is only used to generate synthetic observations.
    It must NEVER be used as an ML feature.
    """

    random_value = random.random()

    if random_value < 0.20:
        # Lower reliability group
        return random.uniform(0.45, 0.65)

    if random_value < 0.70:
        # Medium reliability group
        return random.uniform(0.65, 0.85)

    # High reliability group
    return random.uniform(0.85, 0.97)


def generate_session(
    charger_id,
    timestamp,
    reliability,
):

    success = (
        random.random()
        < reliability
    )

    duration = random.uniform(
        10,
        60,
    )

    energy = random.uniform(
        4,
        35,
    )

    failure_reason = None

    if not success:

        failure_reason = random.choice(
            [
                "connector_fault",
                "communication_error",
                "power_failure",
                "charger_unavailable",
            ]
        )

    return (
        charger_id,
        timestamp,
        timestamp
        + timedelta(
            minutes=duration
        ),
        success,
        round(
            energy,
            2,
        ),
        round(
            duration,
            2,
        ),
        failure_reason,
        "simulated",
    )


def generate_status_event(
    charger_id,
    timestamp,
    reliability,
):

    roll = random.random()

    if roll < reliability:

        status = "available"

    elif roll < (
        reliability + 0.10
    ):

        status = "occupied"

    else:

        status = random.choice(
            [
                "faulted",
                "offline",
            ]
        )

    return (
        charger_id,
        timestamp,
        status,
        "simulated",
    )


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
        f"Selected {len(chargers)} "
        f"chargers for simulation."
    )

    conn = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with conn.cursor() as cur:

            # ----------------------------------
            # Clear ONLY synthetic history
            # ----------------------------------

            cur.execute(
                """
                DELETE FROM charger_status_events
                WHERE charger_id = ANY(%s)
                  AND source = 'simulated'
                """,
                (charger_ids,),
            )

            cur.execute(
                """
                DELETE FROM charger_sessions
                WHERE charger_id = ANY(%s)
                  AND source = 'simulated'
                """,
                (charger_ids,),
            )

            # ----------------------------------
            # History window
            # ----------------------------------

            start = (
                datetime.now(
                    timezone.utc
                )
                - timedelta(
                    days=DAYS_OF_HISTORY
                )
            )

            total_sessions = 0
            total_status_events = 0

            # ----------------------------------
            # Generate each charger's history
            # ----------------------------------

            for index, (
                internal_id,
                charger_id,
            ) in enumerate(chargers):

                reliability = (
                    generate_profile(index)
                )

                current_time = start

                # Different chargers receive
                # different activity volumes.
                daily_sessions = random.randint(
                    2,
                    8,
                )

                daily_status_events = random.randint(
                    3,
                    8,
                )

                for day in range(
                    DAYS_OF_HISTORY
                ):

                    # ------------------------------
                    # Charging sessions
                    # ------------------------------

                    session_count = max(
                        1,
                        int(
                            random.gauss(
                                daily_sessions,
                                1.5,
                            )
                        ),
                    )

                    for _ in range(
                        session_count
                    ):

                        session_time = (
                            current_time
                            + timedelta(
                                minutes=random.randint(
                                    0,
                                    1439,
                                )
                            )
                        )

                        session = generate_session(
                            internal_id,
                            session_time,
                            reliability,
                        )

                        cur.execute(
                            """
                            INSERT INTO charger_sessions (
                                charger_id,
                                started_at,
                                ended_at,
                                session_success,
                                energy_kwh,
                                duration_minutes,
                                failure_reason,
                                source
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                            """,
                            session,
                        )

                        total_sessions += 1

                    # ------------------------------
                    # Status events
                    # ------------------------------

                    event_count = max(
                        1,
                        int(
                            random.gauss(
                                daily_status_events,
                                1.5,
                            )
                        ),
                    )

                    for _ in range(
                        event_count
                    ):

                        event_time = (
                            current_time
                            + timedelta(
                                minutes=random.randint(
                                    0,
                                    1439,
                                )
                            )
                        )

                        event = generate_status_event(
                            internal_id,
                            event_time,
                            reliability,
                        )

                        cur.execute(
                            """
                            INSERT INTO charger_status_events (
                                charger_id,
                                event_time,
                                status,
                                source
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s
                            )
                            """,
                            event,
                        )

                        total_status_events += 1

                    current_time += timedelta(
                        days=1
                    )

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
        print(
            "OPERATIONAL SIMULATION COMPLETE"
        )
        print(
            "=" * 60
        )
        print(
            f"Chargers simulated: "
            f"{len(chargers)}"
        )
        print(
            f"History duration: "
            f"{DAYS_OF_HISTORY} days"
        )
        print(
            f"Sessions generated: "
            f"{total_sessions}"
        )
        print(
            f"Status events generated: "
            f"{total_status_events}"
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