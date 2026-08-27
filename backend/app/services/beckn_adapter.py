"""
Beckn Application Provider (BAP) adapter.

ChargeSure plugs into the Unified Bharat eCharge (UBC) network as an intelligence
layer on top of the open Beckn/OCPI protocol, rather than competing with it.
Phase 1 (hackathon MVP): stubbed responses, no live UBC gateway calls.
Phase 2: replace _call_ubc_gateway with a real httpx POST once sandbox credentials exist.
"""
import uuid
from datetime import datetime
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()


class BecknBAPAdapter:
    def __init__(self):
        self.bap_id = settings.beckn_bap_id
        self.bap_uri = settings.beckn_bap_uri
        self.gateway_url = settings.beckn_ubc_gateway_url

    def _context(self, action: str, transaction_id: Optional[str] = None) -> dict:
        return {
            "domain": "uei:charging",
            "action": action,
            "core_version": "1.1.0",
            "bap_id": self.bap_id,
            "bap_uri": self.bap_uri,
            "transaction_id": transaction_id or str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def search(self, latitude: float, longitude: float, radius_km: float = 10.0) -> dict:
        """Discover chargers via the UBC network (used to supplement our own PostGIS index)."""
        payload = {
            "context": self._context("search"),
            "message": {
                "intent": {
                    "fulfillment": {
                        "stops": [
                            {
                                "location": {
                                    "gps": f"{latitude},{longitude}",
                                    "radius": {"unit": "km", "value": str(radius_km)},
                                }
                            }
                        ]
                    }
                }
            },
        }
        return await self._call_ubc_gateway("/search", payload)

    async def select(self, charger_bpp_id: str, item_id: str, transaction_id: str) -> dict:
        payload = {
            "context": self._context("select", transaction_id),
            "message": {"order": {"provider": {"id": charger_bpp_id}, "items": [{"id": item_id}]}},
        }
        return await self._call_ubc_gateway("/select", payload)

    async def init_order(self, transaction_id: str, order_payload: dict) -> dict:
        payload = {
            "context": self._context("init", transaction_id),
            "message": {"order": order_payload},
        }
        return await self._call_ubc_gateway("/init", payload)

    async def confirm(self, transaction_id: str, order_payload: dict) -> dict:
        payload = {
            "context": self._context("confirm", transaction_id),
            "message": {"order": order_payload},
        }
        return await self._call_ubc_gateway("/confirm", payload)

    async def _call_ubc_gateway(self, path: str, payload: dict) -> dict:
        if settings.environment != "production":
            # Stub response for local/hackathon use — no live UBC sandbox yet.
            return {
                "context": payload["context"],
                "message": {"ack": {"status": "ACK"}},
                "_stubbed": True,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.gateway_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()


beckn_adapter = BecknBAPAdapter()
