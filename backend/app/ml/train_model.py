"""
Offline training script for the reliability classifier.
Run manually or via the nightly retraining pipeline (see app/tasks/nightly_retrain.py).

Usage:
    python -m app.ml.train_model
"""
import os
from datetime import datetime

import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss

from app.database import SessionLocal
from app.models import Charger
from app.ml.features import build_training_dataframe, FEATURE_COLUMNS
from app.config import get_settings

settings = get_settings()


def train() -> str:
    db = SessionLocal()
    try:
        chargers = db.query(Charger).filter(Charger.is_active == True).all()  # noqa: E712
        df = build_training_dataframe(db, chargers)

        if len(df) < 30:
            raise RuntimeError(
                f"Only {len(df)} labelled chargers available — need at least 30 to train. "
                "Cold-start: fall back to the Bayesian prior baseline instead."
            )

        X = df[FEATURE_COLUMNS]
        y = df["label"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:logistic",  # outputs a 0-1 probability-like score
            random_state=42,
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        auc = roc_auc_score((y_test > 0.5).astype(int), preds) if y_test.nunique() > 1 else float("nan")
        brier = brier_score_loss(y_test, preds)
        print(f"[train_model] AUC={auc:.3f} Brier={brier:.3f} n_train={len(X_train)} n_test={len(X_test)}")

        os.makedirs(os.path.dirname(settings.reliability_model_path), exist_ok=True)
        model.save_model(settings.reliability_model_path)

        version = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        with open(settings.reliability_model_path + ".version", "w") as f:
            f.write(version)

        print(f"[train_model] Saved model version {version} to {settings.reliability_model_path}")
        return version
    finally:
        db.close()


if __name__ == "__main__":
    train()
