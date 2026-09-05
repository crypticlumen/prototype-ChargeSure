import psycopg2

from app.config import get_settings


settings = get_settings()

MODEL_VERSION = "xgboost-v1"


def get_reliability_score(charger_id: str) -> float:
    details = get_reliability_details(charger_id)
    return details["reliability_score"]


def get_reliability_details(charger_id: str) -> dict:
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

    # Use ChargeSure's central DATABASE_URL.
    # Local development and Render production can therefore
    # use the same reliability code.
    connection = psycopg2.connect(settings.database_url)

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (charger_id, MODEL_VERSION))
            result = cursor.fetchone()

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

            return {
                "charger_id": charger_id,
                "reliability_score": float(result[0]),
                "prediction_probability": float(result[1]),
                "confidence": result[2],
                "model_version": result[3],
                "predicted_at": result[4],
                "available": True,
            }
    finally:
        connection.close()


def get_operational_signals(charger_id: str) -> dict:
    """
    Return operational and crowd-report signals for a charger.

    Availability remains primarily driven by the historical availability
    ratio, but crowd reports now contribute when reports exist:

        70% historical availability
        30% positive crowd-status ratio

    Chargers with no crowd reports keep their historical availability score.
    """

    query = """
        SELECT
            availability_ratio,
            average_crowd_trust,
            positive_report_ratio,
            negative_report_ratio,
            total_sessions,
            total_status_events,
            crowd_report_count
        FROM reliability_features
        WHERE charger_id = %s
        LIMIT 1;
    """

    # Use the same configured database connection as the
    # main ChargeSure application.
    connection = psycopg2.connect(settings.database_url)

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (charger_id,))
            result = cursor.fetchone()

            if result is None:
                return {
                    "availability_score": 50.0,
                    "trust_score": 50.0,
                    "positive_report_ratio": 0.50,
                    "negative_report_ratio": 0.50,
                    "total_sessions": 0,
                    "total_status_events": 0,
                    "crowd_report_count": 0,
                    "crowd_signal_score": 50.0,
                    "crowd_signal_strength": 0.0,
                }

            availability_ratio = float(result[0] or 0.0)
            average_crowd_trust = float(result[1] or 50.0)
            positive_report_ratio = float(result[2] or 0.0)
            negative_report_ratio = float(result[3] or 0.0)
            total_sessions = int(result[4] or 0)
            total_status_events = int(result[5] or 0)
            crowd_report_count = int(result[6] or 0)

            base_availability_score = availability_ratio * 100.0
            crowd_signal_score = positive_report_ratio * 100.0

            if crowd_report_count > 0:
                availability_score = (
                    0.70 * base_availability_score
                    + 0.30 * crowd_signal_score
                )
                crowd_signal_strength = 0.30
            else:
                availability_score = base_availability_score
                crowd_signal_strength = 0.0

            return {
                "availability_score": round(availability_score, 2),
                "trust_score": round(average_crowd_trust, 2),
                "positive_report_ratio": round(
                    positive_report_ratio,
                    4,
                ),
                "negative_report_ratio": round(
                    negative_report_ratio,
                    4,
                ),
                "total_sessions": total_sessions,
                "total_status_events": total_status_events,
                "crowd_report_count": crowd_report_count,
                "crowd_signal_score": round(
                    crowd_signal_score,
                    2,
                ),
                "crowd_signal_strength": crowd_signal_strength,
            }
    finally:
        connection.close()