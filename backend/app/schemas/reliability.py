from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReliabilityScoreOut(BaseModel):
    charger_id: UUID
    score: float  # 0-100
    confidence_band: str  # low | medium | high
    model_version: str
    computed_at: datetime

    class Config:
        from_attributes = True
