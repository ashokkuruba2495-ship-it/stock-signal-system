from fastapi import APIRouter, HTTPException
from typing import List, Dict

from app.core.config import WATCHLIST, SYMBOLS, THRESHOLDS, logger
from app.schemas.models import (
    SignalResponse, BacktestResponse, ThresholdUpdate, RecipientUpdate,
    SignalHistoryEntry,
)
from app.services.ml_service import predict_signal, backtest_strategy, clear_cache
from app.services.alert_service import get_alert_state, get_recipient, update_recipient
from app.services.history_service import get_history, get_all_latest, get_tickers_with_history
from app.services.data_service import fetch_stock_data, clean_data, add_features

router = APIRouter()

# ── Signals ───────────────────────────────────────────────────────────────────

@router.get("/signals/all", response_model=List[SignalResponse])
async def get_all_signals():
    """Fetch active signals for all tracked stocks."""
    results = []
    for ticker in WATCHLIST:
        try:
            res = predict_signal(ticker)
            results.append(SignalResponse(**res))
        except Exception as e:
            logger.error(f"signals/all failed for {ticker}: {e}")
            results.append(SignalResponse(
                ticker=ticker,
                yf_symbol=SYMBOLS.get(ticker, ticker),
                signal="ERROR",
                probabilities={"BUY": 0.0, "HOLD": 0.0, "SELL": 0.0},
                price=0.0,
                error=str(e),
            ))
    return results

@router.get("/signal/{ticker_name}", response_model=SignalResponse)
async def get_single_signal(ticker_name: str):
    """Fetch signal for a specific stock."""
    try:
        res = predict_signal(ticker_name.upper())
        return SignalResponse(**res)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

# ── Backtest ──────────────────────────────────────────────────────────────────

@router.get("/backtest/{ticker_name}", response_model=BacktestResponse)
async def get_backtest(ticker_name: str):
    """Run historical backtest for a specific stock with full trade log."""
    try:
        res = backtest_strategy(ticker_name.upper())
        return BacktestResponse(**res)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

# ── Signal History ────────────────────────────────────────────────────────────

@router.get("/history/{ticker_name}", response_model=List[SignalHistoryEntry])
async def get_signal_history(ticker_name: str, limit: int = 50):
    """Return past signal readings for one ticker (most recent first)."""
    data = get_history(ticker_name.upper(), limit=limit)
    return data

@router.get("/history", response_model=List[SignalHistoryEntry])
async def get_all_history(limit_per_ticker: int = 5):
    """Return recent signal readings for all tickers."""
    return get_all_latest(limit_per_ticker=limit_per_ticker)

# ── Models Status ─────────────────────────────────────────────────────────────

@router.get("/models/status")
async def get_models_status() -> List[Dict]:
    """Check training status and details of all models."""
    from app.services.ml_service import load_artifacts
    status_list = []
    for ticker in WATCHLIST:
        payload = load_artifacts(ticker)
        if payload:
            status_list.append({
                "ticker": ticker,
                "status": "Ready",
                "model_type": payload.get("model_type", "unknown"),
                "cv_accuracy": payload.get("cv_accuracy"),
                "test_accuracy": payload.get("test_accuracy") or payload.get("accuracy"),
                "trained_at": payload.get("trained_at", "Unknown"),
            })
        else:
            status_list.append({
                "ticker": ticker,
                "status": "Missing",
                "model_type": None,
                "cv_accuracy": None,
                "test_accuracy": None,
                "trained_at": None,
            })
    return status_list

# ── Stock Price Chart Data ────────────────────────────────────────────────────

@router.get("/stock/{symbol}")
async def get_stock_data(symbol: str, days: int = 60):
    """
    Fetch recent historical price data for charting.
    Returns: {"dates": [...], "prices": [...]} with real closing prices.
    """
    try:
        df = fetch_stock_data(symbol)
        df = clean_data(df)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        tail = df.tail(days).copy()

        # Ensure Date is a string (not Timestamp)
        if "Date" in tail.columns:
            tail["Date"] = tail["Date"].astype(str).str[:10]

        # Drop rows where Close is missing or non-finite
        tail = tail[tail["Close"].notna() & tail["Close"].apply(lambda x: float(x) > 0)]

        dates  = tail["Date"].tolist() if "Date" in tail.columns else [str(i) for i in tail.index]
        prices = [round(float(p), 2) for p in tail["Close"].tolist()]

        logger.info(f"[stock/{symbol}] returning {len(dates)} points, last price: {prices[-1] if prices else 'N/A'}")
        return {"dates": dates, "prices": prices}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

# ── Watchlist ─────────────────────────────────────────────────────────────────

@router.get("/watchlist")
async def get_watchlist() -> List[Dict]:
    """Get watchlist with thresholds."""
    return [
        {"ticker": ticker, "symbol": SYMBOLS[ticker], "threshold": THRESHOLDS[ticker]}
        for ticker in WATCHLIST
    ]

# ── Config ────────────────────────────────────────────────────────────────────

@router.post("/config/thresholds")
async def update_thresholds(payload: ThresholdUpdate):
    for ticker, val in payload.thresholds.items():
        if ticker in THRESHOLDS:
            THRESHOLDS[ticker] = val
    return {"message": "Thresholds updated", "thresholds": THRESHOLDS}

@router.post("/config/recipient")
async def update_email_recipient(payload: RecipientUpdate):
    update_recipient(payload.email)
    return {"message": f"Alert recipient updated to {payload.email}"}

# ── Alert Status ──────────────────────────────────────────────────────────────

@router.get("/alerts/status")
async def get_alert_status() -> Dict:
    return {
        "recipient": get_recipient(),
        "state": get_alert_state(),
        "history_tickers": get_tickers_with_history(),
    }

# ── Cache ─────────────────────────────────────────────────────────────────────

@router.post("/cache/clear")
async def clear_model_cache():
    """Force the ML service to drop cached models in case of retraining."""
    clear_cache()
    return {"message": "Model cache cleared successfully."}
