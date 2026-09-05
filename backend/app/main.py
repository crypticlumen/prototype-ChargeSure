import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_postgis
from app.routers import auth, chargers, routes, reliability, booking, beckn, ingestion
from app.tasks.nightly_retrain import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chargesure")

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

app = FastAPI(
    title="ChargeSure API",
    description="EV Mobility Intelligence Platform — reliability-scored, 2W/3W-first charging routes.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "https://chargesure.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chargers.router)
app.include_router(routes.router)
app.include_router(reliability.router)
app.include_router(booking.router)
app.include_router(beckn.router)
app.include_router(ingestion.router)


@app.on_event("startup")
def on_startup():
    logger.info("Starting ChargeSure API in %s mode", settings.environment)

    # The database schema is managed by database/schema/*.sql migrations.
    # Do not call Base.metadata.create_all() here because the ORM metadata
    # contains legacy definitions that do not match the current schema.
    init_postgis()

    if settings.environment != "test":
        start_scheduler()


@app.get("/")
def root():
    return {
        "service": "ChargeSure API",
        "status": "online",
        "version": "0.1.0",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )