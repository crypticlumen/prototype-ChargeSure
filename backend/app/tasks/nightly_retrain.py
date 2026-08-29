import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import Charger
from app.ml.train_model import train
from app.services.reliability_engine import reliability_engine, ReliabilityEngine

logger = logging.getLogger("chargesure.nightly_retrain")


def run_nightly_job() -> None:
    logger.info("Starting nightly retrain + score refresh")

    try:
        train()
        global reliability_engine 
        reliability_engine.__init__()  
    except RuntimeError as e:
        logger.warning("Skipping model retrain this cycle: %s", e)

    db = SessionLocal()
    try:
        chargers = db.query(Charger).filter(Charger.is_active == True).all() 
        for charger in chargers:
            reliability_engine.upsert_score(db, charger)
        logger.info("Refreshed reliability scores for %d chargers", len(chargers))
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(run_nightly_job, "cron", hour=2, minute=30, id="nightly_retrain")
    scheduler.start()
    logger.info("Nightly retrain scheduler started — runs daily at 02:30 IST")
    return scheduler
