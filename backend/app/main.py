import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_postgis
from app.routers import (
    auth,
    chargers,
    routes,
    reliability,
    booking,
    beckn,
    ingestion,
    reports,
)
from app.tasks.nightly_retrain import start_scheduler
from app.routers.reports import ensure_reports_table


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chargesure")

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

app = FastAPI(
    title="ChargeSure API",
    description=(
        "EV Mobility Intelligence Platform — "
        "reliability-scored, 2W/3W-first charging routes."
    ),
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# Explicitly allow the local Vite frontend.
# This avoids wildcard + credentials issues in browsers.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API routers
app.include_router(auth.router)
app.include_router(chargers.router)
app.include_router(routes.router)
app.include_router(reliability.router)
app.include_router(booking.router)
app.include_router(beckn.router)
app.include_router(ingestion.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    logger.info(
        "Starting ChargeSure API in %s mode",
        settings.environment,
    )

    init_postgis()

    # Ensure the crowd_reports table exists.
    ensure_reports_table()

    if settings.environment != "test":
        start_scheduler()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled error on %s",
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

