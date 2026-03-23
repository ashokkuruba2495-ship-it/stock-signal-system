import os
import logging
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stock_signal")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(BASE_DIR), "models"))
os.makedirs(MODEL_DIR, exist_ok=True)

# Watchlist Definition
WATCHLIST_MAP: Dict[str, tuple] = {
    "RELIANCE":   ("RELIANCE.NS",   2500),
    "TCS":        ("TCS.NS",        3500),
    "HDFCBANK":   ("HDFCBANK.NS",   1600),
    "INFY":       ("INFY.NS",       1400),
    "ICICIBANK":  ("ICICIBANK.NS",  1000),
    "HINDUNILVR": ("HINDUNILVR.NS", 2400),
    "ITC":        ("ITC.NS",         450),
    "SBIN":       ("SBIN.NS",        750),
    "BHARTIARTL": ("BHARTIARTL.NS", 1200),
    "KOTAKBANK":  ("KOTAKBANK.NS",  1700),
}

WATCHLIST = list(WATCHLIST_MAP.keys())
SYMBOLS = {k: v[0] for k, v in WATCHLIST_MAP.items()}
THRESHOLDS = {k: v[1] for k, v in WATCHLIST_MAP.items()}

class Settings:
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

settings = Settings()
