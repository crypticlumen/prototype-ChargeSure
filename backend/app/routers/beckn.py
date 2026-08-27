from fastapi import APIRouter, Request

router = APIRouter(prefix="/beckn", tags=["beckn"])

# UBC gateway calls these on_* callback endpoints asynchronously after we call
# search/select/init/confirm on the BAP client (app/services/beckn_adapter.py).
# Phase 1 stubs just acknowledge receipt; Phase 2 wires these into the booking/trip flow.


@router.post("/on_search")
async def on_search(request: Request):
    body = await request.json()
    # TODO Phase 2: merge UBC-network chargers into our PostGIS index via openchargemap_service-style upsert
    return {"context": body.get("context", {}), "message": {"ack": {"status": "ACK"}}}


@router.post("/on_select")
async def on_select(request: Request):
    body = await request.json()
    return {"context": body.get("context", {}), "message": {"ack": {"status": "ACK"}}}


@router.post("/on_init")
async def on_init(request: Request):
    body = await request.json()
    return {"context": body.get("context", {}), "message": {"ack": {"status": "ACK"}}}


@router.post("/on_confirm")
async def on_confirm(request: Request):
    body = await request.json()
    # TODO Phase 2: update the matching Booking.status based on the UBC-confirmed order
    return {"context": body.get("context", {}), "message": {"ack": {"status": "ACK"}}}
