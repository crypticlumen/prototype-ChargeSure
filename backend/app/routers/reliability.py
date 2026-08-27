from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Charger
from app.schemas.reliability import ReliabilityScoreOut
from app.services.reliability_engine import reliability_engine

router = APIRouter(prefix="/reliability", tags=["reliability"])


@router.get("/{charger_id}", response_model=ReliabilityScoreOut)
def get_reliability(charger_id: UUID, db: Session = Depends(get_db)):
    charger = db.query(Charger).filter(Charger.id == charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")

    record = reliability_engine.upsert_score(db, charger)
    return record


@router.post("/{charger_id}/recompute", response_model=ReliabilityScoreOut)
def recompute_reliability(charger_id: UUID, db: Session = Depends(get_db)):
    """Force a recompute outside the nightly schedule — useful right after a new crowd report."""
    charger = db.query(Charger).filter(Charger.id == charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")

    record = reliability_engine.upsert_score(db, charger)
    return record
