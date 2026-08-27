from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point

from app.database import get_db
from app.models import Charger, CrowdReport, User
from app.schemas.charger import ChargerOut, ChargerCreate, CrowdReportCreate
from app.services.reliability_engine import reliability_engine
from app.utils.geo import find_chargers_near
from app.utils.security import get_current_user

router = APIRouter(prefix="/chargers", tags=["chargers"])

# Geofence radius for crowd check-in confirmation — reports outside this are still
# accepted but flagged as unconfirmed and weighted lower by the reliability engine.
GEOFENCE_RADIUS_METERS = 150


def _to_out(db: Session, charger: Charger) -> ChargerOut:
    lat_lng = to_shape(charger.location)
    score, confidence, _ = reliability_engine.score_charger(db, charger)
    return ChargerOut(
        id=charger.id,
        name=charger.name,
        address=charger.address,
        latitude=lat_lng.y,
        longitude=lat_lng.x,
        connector_types=charger.connector_types.split(","),
        supports_2w=charger.supports_2w,
        supports_3w=charger.supports_3w,
        supports_4w=charger.supports_4w,
        max_power_kw=charger.max_power_kw,
        last_verified_at=charger.last_verified_at,
        is_active=charger.is_active,
        reliability_score=score,
        confidence_band=confidence,
    )


@router.get("/nearby", response_model=List[ChargerOut])
def nearby_chargers(
    lat: float,
    lng: float,
    radius_km: float = 5.0,
    vehicle_class: Optional[str] = None,
    db: Session = Depends(get_db),
):
    chargers = find_chargers_near(db, lat, lng, radius_km, vehicle_class)
    return [_to_out(db, c) for c in chargers]


@router.get("/{charger_id}", response_model=ChargerOut)
def get_charger(charger_id: UUID, db: Session = Depends(get_db)):
    charger = db.query(Charger).filter(Charger.id == charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    return _to_out(db, charger)


@router.post("", response_model=ChargerOut, status_code=201)
def create_charger(payload: ChargerCreate, db: Session = Depends(get_db)):
    charger = Charger(
        external_id=payload.external_id,
        cpo_id=payload.cpo_id,
        name=payload.name,
        address=payload.address,
        location=from_shape(Point(payload.longitude, payload.latitude), srid=4326),
        connector_types=",".join(payload.connector_types),
        supports_2w=payload.supports_2w,
        supports_3w=payload.supports_3w,
        supports_4w=payload.supports_4w,
        max_power_kw=payload.max_power_kw,
    )
    db.add(charger)
    db.commit()
    db.refresh(charger)
    return _to_out(db, charger)


@router.post("/crowd-reports", status_code=201)
def submit_crowd_report(
    payload: CrowdReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    charger = db.query(Charger).filter(Charger.id == payload.charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")

    charger_point = to_shape(charger.location)
    reporter_point = Point(payload.longitude, payload.latitude)
    # Rough planar distance check; fine at this radius. Swap for ST_DWithin if precision matters.
    distance_deg = charger_point.distance(reporter_point)
    is_geofenced = distance_deg * 111_000 <= GEOFENCE_RADIUS_METERS  # ~meters per degree at equator

    report = CrowdReport(
        charger_id=payload.charger_id,
        user_id=current_user.id,
        reported_status=payload.reported_status,
        reporter_trust_score=current_user.trust_score,
        is_geofenced_confirmed=is_geofenced,
        notes=payload.notes,
    )
    db.add(report)
    db.commit()

    return {"status": "recorded", "geofenced_confirmed": is_geofenced}
