import warnings
import gc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import logger
from app.routes.api import router
from app.services.alert_service import run_alerts

# Suppress ResourceWarning from yfinance/requests_cache SQLite connections
warnings.filterwarnings("ignore", category=ResourceWarning)

app = FastAPI(title="Stock Signal Backend - Redesigned")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    logger.info("Starting up FastAPI application...")
    scheduler.add_job(run_alerts, "interval", minutes=5)
    run_alerts()
    scheduler.start()
    logger.info("Alert scheduler started (every 5 min).")

@app.on_event("shutdown")
def shutdown_event():
    # Stop the alert scheduler gracefully
    try:
        scheduler.shutdown(wait=False)
        logger.info("Alert scheduler stopped.")
    except Exception:
        pass

    # Drop cached ML models from memory
    try:
        from app.services.ml_service import clear_cache
        clear_cache()
        logger.info("ML model cache cleared.")
    except Exception:
        pass

    # Force garbage collection to close any dangling file handles
    gc.collect()
    logger.info("Shutdown complete — all resources released.")

@app.get("/")
def home():
    return {"message": "Stock Signal Backend Running - Redesigned Architecture"}