import os
from datetime import datetime
from typing import Tuple

import xgboost as xgb
import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Charger, ReliabilityScore
from app.ml.features import build_feature_row, FEATURE_COLUMNS

settings = get_settings()

MIN_SESSIONS_FOR_MODEL = 5  # below this, use the Bayesian prior instead of the ML model


class ReliabilityEngine:
    """
    Wraps the trained XGBoost model. Falls back to a Bayesian prior (seeded from the
    ~18% govt non-operational baseline) for chargers with insufficient session history —
    this is the cold-start mitigation described in the pitch.
    """

    def __init__(self):
        self._model = None
        self._model_version = "prior-only"
        self._load_model()

    def _load_model(self) -> None:
        path = settings.reliability_model_path
        if os.path.exists(path):
            model = xgb.XGBRegressor()
            model.load_model(path)
            self._model = model
            version_path = path + ".version"
            if os.path.exists(version_path):
                with open(version_path) as f:
                    self._model_version = f.read().strip()

    def score_charger(self, db: Session, charger: Charger) -> Tuple[float, str, str]:
        """Returns (score_0_to_100, confidence_band, model_version)."""
        features = build_feature_row(db, charger)
        session_count = features["session_count_30d"]

        if self._model is not None and session_count >= MIN_SESSIONS_FOR_MODEL:
            X = pd.DataFrame([features])[FEATURE_COLUMNS]
            raw_score = float(self._model.predict(X)[0])
            raw_score = min(max(raw_score, 0.0), 1.0)
            confidence = self._confidence_band(session_count, features["crowd_report_count_7d"])
            version = self._model_version
        else:
            raw_score = self._bayesian_prior(features)
            confidence = "low"
            version = "bayesian-prior"

        return round(raw_score * 100, 1), confidence, version

    def _bayesian_prior(self, features: dict) -> float:
        """
        Seeds from the govt operational baseline (1 - 0.18 non-operational rate) and
        updates with whatever crowd/session signal exists, however sparse.
        """
        prior = settings.reliability_prior_baseline  # e.g. 0.82
        prior_weight = 10  # pseudo-observations behind the prior

        successes = features["session_success_rate_30d"] * features["session_count_30d"]
        observed_weight = features["session_count_30d"]

        crowd_penalty = features["crowd_report_failure_rate_7d"] * min(
            features["crowd_report_count_7d"], 5
        )

        posterior = (
            (prior * prior_weight) + successes - crowd_penalty
        ) / (prior_weight + observed_weight)

        return min(max(posterior, 0.0), 1.0)

    @staticmethod
    def _confidence_band(session_count: int, crowd_report_count: int) -> str:
        signal = session_count + crowd_report_count
        if signal >= 20:
            return "high"
        if signal >= 8:
            return "medium"
        return "low"

    def upsert_score(self, db: Session, charger: Charger) -> ReliabilityScore:
        score, confidence, version = self.score_charger(db, charger)

        record = (
            db.query(ReliabilityScore)
            .filter(ReliabilityScore.charger_id == charger.id)
            .first()
        )
        if record is None:
            record = ReliabilityScore(charger_id=charger.id)
            db.add(record)

        record.score = score
        record.confidence_band = confidence
        record.model_version = version
        record.computed_at = datetime.utcnow()

        db.commit()
        db.refresh(record)
        return record


reliability_engine = ReliabilityEngine()
