from typing import Dict


# Temporary values for development.
# These will later be replaced by XGBoost predictions.

RELIABILITY_SCORES: Dict[str, float] = {
    "OCM-502298": 80.0,
    "OCM-502299": 80.0,
    "OCM-502309": 88.0,
    "OCM-502321": 92.0,
    "OCM-502308": 78.0,
    "OCM-502313": 84.0,
    "OCM-502314": 71.0,
    "OCM-502283": 75.0,
    "OCM-502288": 68.0,
    "OCM-502306": 61.0,
}


def get_reliability_score(
    charger_id: str,
) -> float:

    return RELIABILITY_SCORES.get(
        charger_id,
        50.0,
    )