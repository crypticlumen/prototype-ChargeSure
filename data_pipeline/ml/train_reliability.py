from pathlib import Path

import joblib
import pandas as pd
import psycopg2

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from sklearn.model_selection import train_test_split

from xgboost import XGBClassifier


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


# ---------------------------------------------------------
# Model configuration
# ---------------------------------------------------------

MODEL_DIR = Path(
    "data_pipeline/ml/models"
)

MODEL_FILE = (
    MODEL_DIR
    / "reliability_xgb.json"
)

METADATA_FILE = (
    MODEL_DIR
    / "reliability_features.joblib"
)


# ---------------------------------------------------------
# Features
# ---------------------------------------------------------

FEATURE_COLUMNS = [
    "total_sessions",
    "successful_sessions",
    "failed_sessions",
    "session_success_rate",
    "avg_energy_kwh",
    "avg_session_duration_minutes",

    "total_status_events",
    "available_events",
    "occupied_events",
    "faulted_events",
    "offline_events",

    "availability_ratio",
    "fault_ratio",
    "offline_ratio",

    "crowd_report_count",
    "average_crowd_trust",
    "positive_report_ratio",
    "negative_report_ratio",

    "power_kw",
    "days_since_verification",
]


def load_training_data() -> pd.DataFrame:
    """
    Load the engineered training dataset
    directly from PostgreSQL.
    """

    query = """
        SELECT
            charger_id,

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
            days_since_verification,

            reliable_label

        FROM reliability_training

        WHERE reliable_label IS NOT NULL
    """

    conn = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        return pd.read_sql_query(
            query,
            conn,
        )

    finally:
        conn.close()


def prepare_features(
    df: pd.DataFrame,
):
    """
    Prepare X and y for training.
    """

    X = df[
        FEATURE_COLUMNS
    ].copy()

    y = df[
        "reliable_label"
    ].astype(int)

    # XGBoost can handle missing values,
    # but replacing infinite values is still useful.
    X = X.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    return X, y


def train_model(
    X_train,
    y_train,
):

    model = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,

        objective="binary:logistic",
        eval_metric="logloss",

        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
    )

    return model

def print_feature_importance(model):

    importances = model.feature_importances_

    feature_importance = sorted(
        zip(
            FEATURE_COLUMNS,
            importances,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    print()
    print(
        "FEATURE IMPORTANCE"
    )
    print("=" * 60)

    for feature, importance in feature_importance:
        print(
            f"{feature:35s} "
            f"{importance:.4f}"
        )

def evaluate_model(
    model,
    X_test,
    y_test,
):

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    try:
        auc = roc_auc_score(
            y_test,
            probabilities,
        )
    except ValueError:
        auc = float("nan")

    print()
    print(
        "MODEL EVALUATION"
    )
    print("=" * 60)

    print(
        f"Accuracy:  {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1:        {f1:.4f}"
    )

    print(
        f"ROC-AUC:   {auc:.4f}"
    )

    print()
    print(
        "Classification report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print(
        "Confusion matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            predictions,
        )
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
    }


def main():

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Loading reliability training data..."
    )

    df = load_training_data()

    if df.empty:
        raise RuntimeError(
            "No training data found."
        )

    print(
        f"Training rows: {len(df)}"
    )

    print(
        "Class distribution:"
    )

    print(
        df["reliable_label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    X, y = prepare_features(df)

    print()
    print(
        f"Features: {len(FEATURE_COLUMNS)}"
    )

    print(
        "Feature columns:"
    )

    for feature in FEATURE_COLUMNS:
        print(
            f"  - {feature}"
        )

    # --------------------------------------------------
    # Stratified train/test split
    # --------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )
    )

    print()
    print(
        f"Training set: {len(X_train)}"
    )

    print(
        f"Test set:     {len(X_test)}"
    )

    # --------------------------------------------------
    # Train
    # --------------------------------------------------

    print()
    print(
        "Training XGBoost..."
    )

    model = train_model(
        X_train,
        y_train,
    )
    print_feature_importance(model)

    # --------------------------------------------------
    # Evaluate
    # --------------------------------------------------

    metrics = evaluate_model(
        model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    model.save_model(
        MODEL_FILE
    )

    # Save feature metadata.
    joblib.dump(
        {
            "feature_columns": FEATURE_COLUMNS,
            "metrics": metrics,
        },
        METADATA_FILE,
    )

    print()
    print(
        "MODEL SAVED"
    )
    print("=" * 60)

    print(
        f"Model: {MODEL_FILE}"
    )

    print(
        f"Metadata: {METADATA_FILE}"
    )


if __name__ == "__main__":
    main()