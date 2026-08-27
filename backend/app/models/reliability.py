import uuid
from datetime import datetime

from sqlalchemy import Column, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ReliabilityScore(Base):
    """Latest ML-computed reliability score per charger. Recomputed on the nightly job."""
    __tablename__ = "reliability_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    charger_id = Column(UUID(as_uuid=True), ForeignKey("chargers.id"), nullable=False, unique=True)

    score = Column(Float, nullable=False)  # 0-100
    confidence_band = Column(String, nullable=False)  # "low" | "medium" | "high"
    model_version = Column(String, nullable=False)

    computed_at = Column(DateTime, default=datetime.utcnow)
