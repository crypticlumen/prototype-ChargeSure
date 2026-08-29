from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.openchargemap_service import openchargemap_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/openchargemap")
async def ingest_openchargemap(
    lat: float, lng: float, distance_km: float = 50, db: Session = Depends(get_db)
):

    raw_pois = await openchargemap_service.fetch_chargers(lat, lng, distance_km)
    created_count = openchargemap_service.upsert_chargers(db, raw_pois)
    return {"fetched": len(raw_pois), "created": created_count}
