from fastapi import APIRouter, Request

router = APIRouter(prefix="/beckn", tags=["beckn"])

@router.post("/on_search")
async def on_search(request: Request):
    body = await request.json()
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
    return {"context": body.get("context", {}), "message": {"ack": {"status": "ACK"}}}
