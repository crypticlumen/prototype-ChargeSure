from pathlib import Path

import joblib
import pandas as pd
import psycopg2
from xgboost import XGBClassifier


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
# Model files
# =========================================================

MODEL_FILE = Path(
    "data_pipeline/ml/models/reliability_xgb.json"
)

METADATA_FILE = Path(
    "data_pipeline/ml/models/reliability_features.joblib"
)

MODEL_VERSION = "xgboost-v1"


# =========================================================
# Load trained XGBoost model
# =========================================================

def load_model():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    model = XGBClassifier()

    model.load_model(
        MODEL_FILE
    )

    return model


# =========================================================
# Load model metadata
# =========================================================

def load_metadata():

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata not found: {METADATA_FILE}"
        )

    return joblib.load(
        METADATA_FILE
    )


# =========================================================
# Load current charger features
# =========================================================

def load_features():

    query = """
        SELECT
            charger_id,
            name,

            total_sessions,
            successful_sessions,
            failed_sessions,
            session_success_rate,
            avg_energy_kwh,
            avg_session_duration_minutes,

            total_status_events,
            available_events,
            occupied_events,
            faulted_events,
            offline_events,

            availability_ratio,
            fault_ratio,
            offline_ratio,

            crowd_report_count,
            average_crowd_trust,
            positive_report_ratio,
            negative_report_ratio,

            power_kw,
            days_since_verification

        FROM current_reliability_features

        WHERE total_sessions > 0

        ORDER BY charger_db_id;
    """

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query
            )

            rows = cursor.fetchall()

            columns = [
                description[0]
                for description in cursor.description
            ]

            return pd.DataFrame(
                rows,
                columns=columns,
            )

    finally:
        connection.close()


# =========================================================
# Determine prediction confidence
# =========================================================

def get_confidence_band(
    probability: float,
    total_sessions: int,
    total_status_events: int,
    crowd_report_count: int,
) -> str:
    """
    Prototype evidence-based confidence band.

    This is NOT a statistical confidence interval.

    It describes the amount of supporting historical
    evidence available to the prediction.
    """

    evidence_count = (
        total_sessions
        + total_status_events
        + crowd_report_count
    )

    if (
        evidence_count >= 500
        and (
            probability >= 0.85
            or probability <= 0.15
        )
    ):
        return "high"

    if (
        evidence_count >= 200
        and (
            probability >= 0.70
            or probability <= 0.30
        )
    ):
        return "medium"

    return "low"


# =========================================================
# Save predictions to PostgreSQL
# =========================================================

def save_predictions(
    df: pd.DataFrame,
    model_version: str,
):

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        with connection.cursor() as cursor:

            for _, row in df.iterrows():

                cursor.execute(
                    """
                    INSERT INTO charger_reliability_predictions (
                        charger_id,
                        reliability_score,
                        prediction_probability,
                        confidence,
                        model_version,
                        prediction_source,
                        predicted_at
                    )
                    SELECT
                        c.id,
                        %s,
                        %s,
                        %s,
                        %s,
                        'xgboost',
                        NOW()
                    FROM chargers c
                    WHERE c.charger_id = %s

                    ON CONFLICT (
                        charger_id,
                        model_version
                    )
                    DO UPDATE SET
                        reliability_score =
                            EXCLUDED.reliability_score,

                        prediction_probability =
                            EXCLUDED.prediction_probability,

                        confidence =
                            EXCLUDED.confidence,

                        prediction_source =
                            EXCLUDED.prediction_source,

                        predicted_at =
                            EXCLUDED.predicted_at;
                    """,
                    (
                        float(
                            row["reliability_score"]
                        ),

                        float(
                            row["prediction_probability"]
                        ),

                        str(
                            row["confidence"]
                        ),

                        model_version,

                        row["charger_id"],
                    ),
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:
        connection.close()


# =========================================================
# Main prediction pipeline
# =========================================================

def main():

    print(
        "LOADING RELIABILITY MODEL..."
    )

    # -----------------------------------------------------
    # Load model
    # -----------------------------------------------------

    model = load_model()

    # -----------------------------------------------------
    # Load metadata
    # -----------------------------------------------------

    metadata = load_metadata()

    feature_columns = metadata[
        "feature_columns"
    ]

    print(
        f"Expected features: "
        f"{len(feature_columns)}"
    )

    # -----------------------------------------------------
    # Load current charger features
    # -----------------------------------------------------

    df = load_features()

    if df.empty:

        raise RuntimeError(
            "No charger feature data available."
        )

    print(
        f"Chargers with feature data: "
        f"{len(df)}"
    )

    # -----------------------------------------------------
    # Validate model features
    # -----------------------------------------------------

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in df.columns
    ]

    if missing_features:

        raise RuntimeError(
            "Missing model features: "
            + ", ".join(
                missing_features
            )
        )

    # -----------------------------------------------------
    # Prepare feature matrix
    # -----------------------------------------------------

    X = df[
        feature_columns
    ].copy()

    X = X.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    for column in feature_columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

    # -----------------------------------------------------
    # Predict
    # -----------------------------------------------------

    probabilities = (
        model.predict_proba(X)[:, 1]
    )

    df[
        "prediction_probability"
    ] = probabilities

    df[
        "reliability_score"
    ] = (
        probabilities * 100
    ).round(2)

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    df["confidence"] = df.apply(
        lambda row: get_confidence_band(
            probability=float(
                row[
                    "prediction_probability"
                ]
            ),

            total_sessions=int(
                row[
                    "total_sessions"
                ]
            ),

            total_status_events=int(
                row[
                    "total_status_events"
                ]
            ),

            crowd_report_count=int(
                row[
                    "crowd_report_count"
                ]
            ),
        ),
        axis=1,
    )

    # -----------------------------------------------------
    # Save to database
    # -----------------------------------------------------

    print()
    print(
        "SAVING PREDICTIONS TO POSTGRESQL..."
    )

    save_predictions(
        df,
        MODEL_VERSION,
    )

    print(
        f"Saved {len(df)} predictions "
        f"to PostgreSQL."
    )

    # -----------------------------------------------------
    # Display predictions
    # -----------------------------------------------------

    print()
    print(
        "CHARGER RELIABILITY PREDICTIONS"
    )

    print(
        "=" * 100
    )

    for _, row in df.iterrows():

        print(
            f"{row['charger_id']} | "
            f"{row['name']} | "
            f"score: "
            f"{row['reliability_score']:.2f} | "
            f"confidence: "
            f"{row['confidence']}"
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print(
        "SUMMARY"
    )

    print(
        "=" * 100
    )

    print(
        f"Predictions generated: "
        f"{len(df)}"
    )

    print(
        f"Average reliability: "
        f"{df['reliability_score'].mean():.2f}"
    )

    print(
        f"Minimum reliability: "
        f"{df['reliability_score'].min():.2f}"
    )

    print(
        f"Maximum reliability: "
        f"{df['reliability_score'].max():.2f}"
    )

    print()

    print(
        "Confidence distribution:"
    )

    print(
        df[
            "confidence"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )


if __name__ == "__main__":
    main()