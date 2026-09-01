import httpx
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.config import get_settings
from app.models import Charger

settings = get_settings()


class OpenChargeMapService:

    def __init__(self):
        self.base_url = settings.openchargemap_base_url
        self.api_key = settings.openchargemap_api_key

    async def fetch_chargers(self, lat: float, lng: float, distance_km: float = 50, max_results: int = 500) -> list:
        params = {
            "output": "json",
            "latitude": lat,
            "longitude": lng,
            "distance": distance_km,
            "distanceunit": "KM",
            "maxresults": max_results,
            "compact": "true",
            "verbose": "false",
        }
        if self.api_key:
            params["key"] = self.api_key

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.base_url}/poi/", params=params)
            resp.raise_for_status()
            return resp.json()

    def upsert_chargers(self, db: Session, raw_pois: list) -> int:
        created = 0
        for poi in raw_pois:
            external_id = str(poi.get("ID"))
            existing = db.query(Charger).filter(Charger.external_id == external_id).first()
            if existing:
                continue

            address_info = poi.get("AddressInfo", {})
            lat, lng = address_info.get("Latitude"), address_info.get("Longitude")
            if lat is None or lng is None:
                continue

            connections = poi.get("Connections", []) or []
            max_power = max(
                (c.get("PowerKW") for c in connections if c.get("PowerKW")), default=None
            )

            charger = Charger(
                external_id=external_id,
                name=address_info.get("Title", "Unnamed Charger"),
                address=address_info.get("AddressLine1"),
                location=from_shape(Point(lng, lat), srid=4326),
                connector_types=",".join(
                    c.get("ConnectionType", {}).get("Title", "UNKNOWN") for c in connections
                ) or "UNKNOWN",
                max_power_kw=max_power,
                is_active=True,
            )
            db.add(charger)
            created += 1

        db.commit()
        return created


openchargemap_service = OpenChargeMapService()
