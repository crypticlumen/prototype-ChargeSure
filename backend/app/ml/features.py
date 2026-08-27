from datetime import datetime
from typing import List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import Charger, ChargingSession, CrowdReport, CPO

FEATURE_COLUMNS = [
    "charger_age_days",
    "days_since_last_verified",
    "operator_reliability_index",
    "session_success_rate_30d",
    "session_count_30d",
    "crowd_report_failure_rate_7d",
    "crowd_report_count_7d",
    "avg_reporter_trust_7d",
]


def build_feature_row(db: Session, charger: Charger, as_of: datetime = None) -> dict:
    """Builds one feature row for a single charger, used both for training and inference."""
    as_of = as_of or datetime.utcnow()

    charger_age_days = (
        (as_of - charger.installed_at).days if charger.installed_at else 365
    )
    days_since_last_verified = (
        (as_of - charger.last_verified_at).days if charger.last_verified_at else 999
    )

    cpo = db.query(CPO).filter(CPO.id == charger.cpo_id).first() if charger.cpo_id else None
    operator_reliability_index = cpo.operator_reliability_index if cpo else 0.5

    sessions_30d = [
        s for s in charger.sessions
        if s.started_at and (as_of - s.started_at).days <= 30
    ]
    session_count_30d = len(sessions_30d)
    session_success_rate_30d = (
        sum(1 for s in sessions_30d if s.was_successful) / session_count_30d
        if session_count_30d > 0 else 0.5  # neutral prior for cold-start
    )

    reports_7d = [
        r for r in charger.crowd_reports
        if r.created_at and (as_of - r.created_at).days <= 7
    ]
    crowd_report_count_7d = len(reports_7d)
    crowd_report_failure_rate_7d = (
        sum(1 for r in reports_7d if r.reported_status in ("broken", "queued")) / crowd_report_count_7d
        if crowd_report_count_7d > 0 else 0.0
    )
    avg_reporter_trust_7d = (
        np.mean([r.reporter_trust_score for r in reports_7d]) if reports_7d else 0.5
    )

    return {
        "charger_age_days": charger_age_days,
        "days_since_last_verified": days_since_last_verified,
        "operator_reliability_index": operator_reliability_index,
        "session_success_rate_30d": session_success_rate_30d,
        "session_count_30d": session_count_30d,
        "crowd_report_failure_rate_7d": crowd_report_failure_rate_7d,
        "crowd_report_count_7d": crowd_report_count_7d,
        "avg_reporter_trust_7d": avg_reporter_trust_7d,
    }


def build_training_dataframe(db: Session, chargers: List[Charger]) -> pd.DataFrame:
    """Label = observed session success rate (ground truth proxy). Used only for offline training."""
    rows = []
    for charger in chargers:
        row = build_feature_row(db, charger)
        successful = sum(1 for s in charger.sessions if s.was_successful)
        total = len(charger.sessions)
        row["label"] = successful / total if total > 0 else np.nan
        rows.append(row)

    df = pd.DataFrame(rows).dropna(subset=["label"])
    return df
