from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReliabilityScoreOut(BaseModel):
    charger_id: UUID
    score: float 
    confidence_band: str 
    model_version: str
    computed_at: datetime

    class Config:
        from_attributes = True
