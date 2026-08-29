from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from geoalchemy2.shape import to_shape

from app.models import Charger


def find_chargers_near(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    vehicle_class: str = None,
    limit: int = 20,
) -> List[Charger]:
    point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    query = db.query(Charger).filter(
        Charger.is_active == True, 
        ST_DWithin(Charger.location, point, radius_km * 1000), 
    )

    if vehicle_class == "2W":
        query = query.filter(Charger.supports_2w == True) 
    elif vehicle_class == "3W":
        query = query.filter(Charger.supports_3w == True) 
    elif vehicle_class == "4W":
        query = query.filter(Charger.supports_4w == True) 

    query = query.order_by(func.ST_Distance(Charger.location, point)).limit(limit)
    return query.all()


def find_chargers_along_route(
    db: Session,
    route_linestring_geojson: dict,
    corridor_width_km: float = 3.0,
    vehicle_class: str = None,
) -> List[Charger]:

    coords = route_linestring_geojson.get("coordinates", [])
    if not coords:
        return []

    wkt_line = "LINESTRING(" + ", ".join(f"{lng} {lat}" for lng, lat in coords) + ")"
    route_geom = func.ST_SetSRID(func.ST_GeomFromText(wkt_line), 4326)

    query = db.query(Charger).filter(
        Charger.is_active == True,  
        ST_DWithin(Charger.location, func.cast(route_geom, type_=Charger.location.type), corridor_width_km * 1000),
    )

    if vehicle_class == "2W":
        query = query.filter(Charger.supports_2w == True)  
    elif vehicle_class == "3W":
        query = query.filter(Charger.supports_3w == True) 

    return query.all()


def charger_lat_lng(charger: Charger) -> tuple:
    point = to_shape(charger.location)
    return point.y, point.x 
