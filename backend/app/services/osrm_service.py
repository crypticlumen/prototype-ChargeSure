import asyncio
import logging
import os
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

logger = logging.getLogger("chargesure.osrm")

RANGE_SAFETY_BUFFER = {
    "2W": 0.80,
    "3W": 0.75,
    "4W": 0.90,
}


class OSRMService:
    """
    Routing service backed by OSRM with Google Directions fallback.

    TLS behavior:
    - Normal HTTPS certificate verification is used first.
    - If the local machine reports a certificate-chain verification error,
      a development-only retry with verify=False is allowed.
    - Set CHARGESURE_ALLOW_INSECURE_TLS=false to disable that retry.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.osrm_base_url).rstrip("/")

    @staticmethod
    def _allow_insecure_tls_fallback() -> bool:
        """
        Development-only escape hatch for environments where HTTPS traffic
        is intercepted by a local proxy/antivirus and presents a certificate
        chain that Python does not trust.

        Defaults to True so the local prototype can continue working.
        Set CHARGESURE_ALLOW_INSECURE_TLS=false for strict TLS verification.
        """
        value = os.getenv("CHARGESURE_ALLOW_INSECURE_TLS", "true").strip().lower()
        return value in {"1", "true", "yes", "on"}

    async def _request_osrm(
        self,
        url: str,
        params: dict,
    ) -> httpx.Response:
        """
        Perform the OSRM request.

        First attempt uses normal TLS verification.
        If the machine reports a certificate verification problem, retry
        once without certificate verification only when explicitly allowed
        by the development setting above.
        """
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                trust_env=True,
            ) as client:
                return await client.get(url, params=params)

        except httpx.ConnectError as exc:
            message = str(exc)

            if (
                "CERTIFICATE_VERIFY_FAILED" not in message
                or not self._allow_insecure_tls_fallback()
            ):
                raise

            logger.warning(
                "OSRM TLS certificate verification failed. "
                "Retrying with certificate verification disabled because "
                "CHARGESURE_ALLOW_INSECURE_TLS is enabled."
            )

            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                trust_env=True,
                verify=False,
            ) as client:
                return await client.get(url, params=params)

    async def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        profile: str = "driving",
    ) -> dict:
        url = (
            f"{self.base_url}/route/v1/{profile}/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        )

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        try:
            resp = await self._request_osrm(url, params)
            resp.raise_for_status()
            data = resp.json()

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning(
                "OSRM request failed: %s. Attempting Google Directions fallback.",
                exc,
            )
            return await self._google_directions_fallback(
                origin_lat,
                origin_lng,
                dest_lat,
                dest_lng,
            )

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning(
                "OSRM returned no usable routes. Response code=%s",
                data.get("code"),
            )
            return await self._google_directions_fallback(
                origin_lat,
                origin_lng,
                dest_lat,
                dest_lng,
            )

        route = data["routes"][0]

        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60, 1),
            "geometry": route["geometry"],
        }

    async def _google_directions_fallback(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict:
        if not settings.google_directions_api_key:
            raise RuntimeError(
                "OSRM unavailable and no Google Directions API key configured"
            )

        url = "https://maps.googleapis.com/maps/api/directions/json"

        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "key": settings.google_directions_api_key,
        }

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            trust_env=True,
        ) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        routes = data.get("routes") or []
        if not routes:
            raise RuntimeError(
                f"Google Directions returned no routes: {data.get('status', 'UNKNOWN')}"
            )

        legs = routes[0].get("legs") or []
        if not legs:
            raise RuntimeError("Google Directions returned no route legs")

        leg = legs[0]

        return {
            "distance_km": round(leg["distance"]["value"] / 1000, 2),
            "duration_minutes": round(leg["duration"]["value"] / 60, 1),
            "geometry": {
                "type": "LineString",
                "coordinates": [],
            },
        }

    @staticmethod
    def safe_range_km(
        vehicle_class: str,
        vehicle_range_km: float,
        current_charge_pct: float,
    ) -> float:
        buffer = RANGE_SAFETY_BUFFER.get(vehicle_class, 0.85)
        charge_fraction = max(0.0, min(current_charge_pct, 100.0)) / 100.0

        return round(
            vehicle_range_km * buffer * charge_fraction,
            1,
        )


async def _self_test() -> None:
    """
    Optional manual test:

        python -m backend.app.services.osrm_service

    This does not require FastAPI to be running.
    """
    service = OSRMService()

    result = await service.get_route(
        origin_lat=17.9577677,
        origin_lng=83.1773604,
        dest_lat=17.9524227,
        dest_lng=83.4163581,
    )

    print("OSRM TEST SUCCESS")
    print(f"Distance: {result['distance_km']} km")
    print(f"Duration: {result['duration_minutes']} minutes")
    print(f"Geometry type: {result['geometry'].get('type')}")


if __name__ == "__main__":
    asyncio.run(_self_test())

