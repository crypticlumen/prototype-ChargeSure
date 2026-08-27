import httpx
from typing import Optional

from app.config import get_settings

settings = get_settings()

# Conservative per-km energy assumptions used to derive "safe range" from vehicle_range_km.
# 2W/3W battery discharge doesn't scale linearly with 4W profiles, so we apply a buffer.
RANGE_SAFETY_BUFFER = {
    "2W": 0.80,   # plan stops at 80% of rated range
    "3W": 0.75,
    "4W": 0.90,
}


class OSRMService:
    """Thin client around a self-hosted OSRM instance, with a Google Directions fallback."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.osrm_base_url

    async def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        profile: str = "driving",
    ) -> dict:
        """Returns distance (km), duration (min), and GeoJSON geometry."""
        url = (
            f"{self.base_url}/route/v1/{profile}/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        )
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError):
                return await self._google_directions_fallback(
                    origin_lat, origin_lng, dest_lat, dest_lng
                )

        if not data.get("routes"):
            return await self._google_directions_fallback(
                origin_lat, origin_lng, dest_lat, dest_lng
            )

        route = data["routes"][0]
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60, 1),
            "geometry": route["geometry"],  # GeoJSON LineString
        }

    async def _google_directions_fallback(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> dict:
        if not settings.google_directions_api_key:
            raise RuntimeError("OSRM unavailable and no Google Directions API key configured")

        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "key": settings.google_directions_api_key,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        leg = data["routes"][0]["legs"][0]
        return {
            "distance_km": round(leg["distance"]["value"] / 1000, 2),
            "duration_minutes": round(leg["duration"]["value"] / 60, 1),
            "geometry": {"type": "LineString", "coordinates": []},  # decode polyline if needed
        }

    @staticmethod
    def safe_range_km(vehicle_class: str, vehicle_range_km: float, current_charge_pct: float) -> float:
        """The distance the rider can safely travel before needing a stop."""
        buffer = RANGE_SAFETY_BUFFER.get(vehicle_class, 0.85)
        return round(vehicle_range_km * buffer * (current_charge_pct / 100), 1)
