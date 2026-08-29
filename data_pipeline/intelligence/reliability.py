import psycopg2


# =========================================================
# Database configuration
# =========================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


# =========================================================
# Active model version
# =========================================================

MODEL_VERSION = "xgboost-v1"


# =========================================================
# Get reliability score
# =========================================================

def get_reliability_score(
    charger_id: str,
) -> float:
    """
    Return the XGBoost reliability score for a charger.

    If no prediction is available, return a neutral
    fallback score of 50.0.
    """

    query = """
        SELECT
            r.reliability_score

        FROM charger_reliability_predictions r

        JOIN chargers c
            ON c.id = r.charger_id

        WHERE c.charger_id = %s
          AND r.model_version = %s

        ORDER BY r.predicted_at DESC

        LIMIT 1;
    """

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    charger_id,
                    MODEL_VERSION,
                ),
            )

            result = cursor.fetchone()

            if result is None:
                return 50.0

            return float(
                result[0]
            )

    finally:
        connection.close()


# =========================================================
# Get complete reliability details
# =========================================================

def get_reliability_details(
    charger_id: str,
) -> dict:
    """
    Return complete reliability information
    for a charger.
    """

    query = """
        SELECT
            r.reliability_score,
            r.prediction_probability,
            r.confidence,
            r.model_version,
            r.predicted_at

        FROM charger_reliability_predictions r

        JOIN chargers c
            ON c.id = r.charger_id

        WHERE c.charger_id = %s
          AND r.model_version = %s

        ORDER BY r.predicted_at DESC

        LIMIT 1;
    """

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    charger_id,
                    MODEL_VERSION,
                ),
            )

            result = cursor.fetchone()

            # -----------------------------------------
            # No prediction available
            # -----------------------------------------

            if result is None:

                return {
                    "charger_id": charger_id,
                    "reliability_score": 50.0,
                    "prediction_probability": 0.50,
                    "confidence": "low",
                    "model_version": MODEL_VERSION,
                    "predicted_at": None,
                    "available": False,
                }

            # -----------------------------------------
            # Prediction exists
            # -----------------------------------------

            return {
                "charger_id": charger_id,
                "reliability_score": float(
                    result[0]
                ),
                "prediction_probability": float(
                    result[1]
                ),
                "confidence": result[2],
                "model_version": result[3],
                "predicted_at": result[4],
                "available": True,
            }

    finally:
        connection.close()


# =========================================================
# Test the reliability layer
# =========================================================

def main():

    test_chargers = [
        "OCM-502321",
        "OCM-502309",
        "OCM-502313",
    ]

    print()
    print(
        "DATABASE-BACKED RELIABILITY"
    )

    print(
        "=" * 90
    )

    for charger_id in test_chargers:

        details = get_reliability_details(
            charger_id
        )

        print(
            f"{charger_id} | "
            f"score: "
            f"{details['reliability_score']:.2f} | "
            f"confidence: "
            f"{details['confidence']} | "
            f"model: "
            f"{details['model_version']} | "
            f"available: "
            f"{details['available']}"
        )


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    main()