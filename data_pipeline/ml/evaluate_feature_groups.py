from pathlib import Path

import pandas as pd
import psycopg2

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from sklearn.model_selection import train_test_split

from xgboost import XGBClassifier


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "chargesure",
    "user": "chargesure",
    "password": "chargesure_dev",
}


BASE_FEATURES = [
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
]


CROWD_FEATURES = [
    "crowd_report_count",
    "average_crowd_trust",
    "positive_report_ratio",
    "negative_report_ratio",
]


METADATA_FEATURES = [
    "power_kw",
    "days_since_verification",
]


def load_data():

    query = """
        SELECT *
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


def train_and_evaluate(
    df,
    features,
    name,
):

    X = df[features].copy()
    y = df["reliable_label"].astype(int)

    X = X.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )
    )

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

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    metrics = {
        "accuracy": accuracy_score(
            y_test,
            predictions,
        ),
        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "f1": f1_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_test,
            probabilities,
        ),
    }

    print()
    print(name)
    print("=" * 70)

    print(
        f"Features: {len(features)}"
    )

    print(
        f"Accuracy:  {metrics['accuracy']:.4f}"
    )

    print(
        f"Precision: {metrics['precision']:.4f}"
    )

    print(
        f"Recall:    {metrics['recall']:.4f}"
    )

    print(
        f"F1:        {metrics['f1']:.4f}"
    )

    print(
        f"ROC-AUC:   {metrics['roc_auc']:.4f}"
    )

    return metrics


def main():

    df = load_data()

    print(
        f"Training rows available: {len(df)}"
    )

    # ----------------------------------------
    # Model A
    # ----------------------------------------

    train_and_evaluate(
        df,
        BASE_FEATURES,
        "MODEL A — OPERATIONAL ONLY",
    )

    # ----------------------------------------
    # Model B
    # ----------------------------------------

    train_and_evaluate(
        df,
        BASE_FEATURES + CROWD_FEATURES,
        "MODEL B — OPERATIONAL + CROWD",
    )

    # ----------------------------------------
    # Model C
    # ----------------------------------------

    train_and_evaluate(
        df,
        BASE_FEATURES
        + CROWD_FEATURES
        + METADATA_FEATURES,
        "MODEL C — ALL FEATURES",
    )


if __name__ == "__main__":
    main()