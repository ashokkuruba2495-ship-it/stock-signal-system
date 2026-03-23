import os
import pickle
import numpy as np
import pandas as pd
from typing import Optional, Dict, List
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

from app.core.config import MODEL_DIR, SYMBOLS, logger
from app.services.data_service import fetch_stock_data, clean_data, compute_advanced_features

# ── In-memory model cache ──────────────────────────────────────────────────────
__model_cache: Dict[str, dict] = {}

# ── Signal thresholds ────────────────────────────────────────────────────────
# Lower thresholds make the system actionable with HOLD-dominant trained models.
# BUY : P(BUY)  must be the leading class AND exceed this floor.
# SELL: P(SELL) must be the leading class AND exceed this floor.
BUY_THRESHOLD  = 0.35
SELL_THRESHOLD = 0.35

_SIGNAL_MAP = {0: "SELL", 1: "HOLD", 2: "BUY"}


def load_artifacts(ticker_name: str) -> Optional[dict]:
    if ticker_name in __model_cache:
        return __model_cache[ticker_name]
    pkl_path = os.path.join(MODEL_DIR, f"{ticker_name}.pkl")
    if not os.path.exists(pkl_path):
        return None
    try:
        with open(pkl_path, "rb") as f:
            payload = pickle.load(f)
        required = {"model", "scaler", "selector", "feature_cols", "selected_features"}
        missing = required - payload.keys()
        if missing:
            logger.warning(f"Corrupt payload for {ticker_name}: missing keys {missing}")
            return None
        __model_cache[ticker_name] = payload
        return payload
    except Exception as e:
        logger.error(f"Error loading artifacts for {ticker_name}: {e}")
        return None


def _apply_threshold(proba_map: dict) -> str:
    """
    Apply relative + floor threshold classification.
    BUY  wins if it is the dominant class and exceeds BUY_THRESHOLD.
    SELL wins if it is the dominant class and exceeds SELL_THRESHOLD.
    Otherwise → HOLD.
    """
    buy_p  = proba_map.get(2, 0.0)   # class 2 = BUY
    sell_p = proba_map.get(0, 0.0)   # class 0 = SELL
    hold_p = proba_map.get(1, 0.0)   # class 1 = HOLD

    # BUY must beat both SELL and HOLD, and exceed floor
    if buy_p > sell_p and buy_p > hold_p and buy_p > BUY_THRESHOLD:
        return "BUY"
    # SELL must beat both BUY and HOLD, and exceed floor
    if sell_p > buy_p and sell_p > hold_p and sell_p > SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


def predict_signal(ticker_name: str) -> dict:
    payload = load_artifacts(ticker_name)
    if payload is None:
        raise FileNotFoundError(f"No trained model available for {ticker_name}")

    model       = payload["model"]
    scaler      = payload["scaler"]
    selector    = payload["selector"]
    feature_cols = payload["feature_cols"]

    yf_symbol = SYMBOLS.get(ticker_name, ticker_name)
    df = fetch_stock_data(yf_symbol)
    df = clean_data(df)
    df = compute_advanced_features(df)

    if df.empty:
        raise ValueError("No data available after feature engineering")

    missing = set(feature_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing features in live data: {missing}")

    X_raw  = df[feature_cols].iloc[[-1]].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_vals = X_raw.values  # strip column names to avoid sklearn warning
    X_scaled = scaler.transform(X_vals)
    X_sel    = selector.transform(X_scaled)

    proba  = model.predict_proba(X_sel)[0]
    classes = list(model.classes_)
    proba_map = {int(c): round(float(p), 4) for c, p in zip(classes, proba)}

    # ── Threshold-based classification ──────────────────────────────────────
    signal_str    = _apply_threshold(proba_map)
    buy_prob      = proba_map.get(2, 0.0)
    sell_prob     = proba_map.get(0, 0.0)
    hold_prob     = proba_map.get(1, 0.0)

    if signal_str == "BUY":
        confidence_pct = round(buy_prob * 100, 1)
    elif signal_str == "SELL":
        confidence_pct = round(sell_prob * 100, 1)
    else:
        confidence_pct = round(hold_prob * 100, 1)

    confidence_str = f"{signal_str} ({confidence_pct:.0f}%)"

    # ── Trend indicator ───────────────────────────────────────────────────────
    sma10 = float(df["SMA_10"].iloc[-1])
    sma50 = float(df["SMA_50"].iloc[-1])
    if sma10 > sma50 * 1.01:
        trend = "↑"
    elif sma10 < sma50 * 0.99:
        trend = "↓"
    else:
        trend = "→"

    test_acc = payload.get("test_accuracy") or payload.get("accuracy")
    price    = round(float(df["Close"].iloc[-1]), 2)

    return {
        "ticker": ticker_name,
        "yf_symbol": yf_symbol,
        "signal": signal_str,
        "confidence": confidence_str,
        "confidence_pct": confidence_pct,
        "trend": trend,
        "buy_prob": buy_prob,
        "sell_prob": sell_prob,
        "probabilities": {
            "SELL": sell_prob,
            "HOLD": hold_prob,
            "BUY": buy_prob,
        },
        "price": price,
        "model_type": payload.get("model_type", "unknown"),
        "cv_accuracy": payload.get("cv_accuracy"),
        "test_accuracy": test_acc,
        "trained_at": payload.get("trained_at"),
    }


def backtest_strategy(ticker_name: str) -> dict:
    """
    Proper position-tracking backtest engine:
    - Enter long on BUY signal
    - Exit on SELL signal
    - HOLD = maintain current position
    Returns summary stats + full trade log + portfolio curve.
    """
    payload = load_artifacts(ticker_name)
    if payload is None:
        raise FileNotFoundError(f"No trained model for {ticker_name}")

    model        = payload["model"]
    scaler       = payload["scaler"]
    selector     = payload["selector"]
    feature_cols = payload["feature_cols"]

    yf_symbol = SYMBOLS.get(ticker_name, ticker_name)
    df = fetch_stock_data(yf_symbol)
    df = clean_data(df)
    df = compute_advanced_features(df)
    df["Daily_Return"] = df["Close"].pct_change()
    df.dropna(inplace=True)

    X = df[feature_cols].replace([np.inf, -np.inf], np.nan).dropna()
    df = df.loc[X.index].copy()

    X_vals   = X.values
    X_scaled = scaler.transform(X_vals)
    X_sel    = selector.transform(X_scaled)
    probas   = model.predict_proba(X_sel)

    classes   = list(model.classes_)
    buy_idx   = classes.index(2) if 2 in classes else -1
    sell_idx  = classes.index(0) if 0 in classes else -1

    # ── Build per-row signal using thresholds ────────────────────────────────
    signals = []
    for row in probas:
        pm = {int(c): round(float(p), 4) for c, p in zip(classes, row)}
        signals.append(_apply_threshold(pm))

    df["signal"] = signals

    # ── Position-tracking trading loop ───────────────────────────────────────
    in_position  = False
    entry_price  = 0.0
    portfolio    = 1.0      # starts at 1 (normalised)
    cash         = 1.0
    shares       = 0.0

    trade_log: List[dict] = []
    curve_dates:  List[str]   = []
    curve_values: List[float] = []
    buy_dates:    List[str]   = []
    sell_dates:   List[str]   = []

    dates  = df["Date"].astype(str).tolist() if "Date" in df.columns else [str(i) for i in df.index]
    closes = df["Close"].tolist()
    sigs   = df["signal"].tolist()

    for i, (date, price, sig) in enumerate(zip(dates, closes, sigs)):
        if not in_position and sig == "BUY":
            # Enter
            shares       = cash / price
            entry_price  = price
            entry_date   = date
            cash         = 0.0
            in_position  = True
            buy_dates.append(date)

        elif in_position and sig == "SELL":
            # Exit
            cash        = shares * price
            shares      = 0.0
            pnl_pct     = (price - entry_price) / entry_price * 100
            trade_log.append({
                "entry_date":  entry_date,
                "exit_date":   date,
                "entry_price": round(entry_price, 2),
                "exit_price":  round(price, 2),
                "pnl_pct":     round(pnl_pct, 2),
                "result":      "WIN" if pnl_pct > 0 else "LOSS",
            })
            in_position  = False
            sell_dates.append(date)

        # Portfolio value
        current_val = cash + shares * price
        curve_dates.append(date)
        curve_values.append(round(current_val, 4))

    # Close any open position at last price
    if in_position:
        last_price = closes[-1]
        cash = shares * last_price
        pnl_pct = (last_price - entry_price) / entry_price * 100
        trade_log.append({
            "entry_date":  entry_date,
            "exit_date":   dates[-1] + " (open)",
            "entry_price": round(entry_price, 2),
            "exit_price":  round(last_price, 2),
            "pnl_pct":     round(pnl_pct, 2),
            "result":      "WIN" if pnl_pct > 0 else "LOSS (open)",
        })

    # ── Market benchmark ─────────────────────────────────────────────────────
    initial_price = closes[0]
    market_curve  = [round(p / initial_price, 4) for p in closes]
    market_return = (closes[-1] / initial_price - 1) * 100

    strategy_return   = (cash - 1.0) * 100
    outperformance    = strategy_return - market_return

    wins        = [t for t in trade_log if "WIN" in t["result"]]
    losses      = [t for t in trade_log if "LOSS" in t["result"]]
    num_trades  = len(trade_log)
    win_rate    = (len(wins) / num_trades * 100) if num_trades > 0 else 0.0

    # Sharpe from curve daily returns
    curve_arr   = np.array(curve_values)
    daily_rets  = np.diff(curve_arr) / (curve_arr[:-1] + 1e-9)
    sharpe      = float(np.sqrt(252) * daily_rets.mean() / (daily_rets.std() + 1e-9))

    rolling_max = np.maximum.accumulate(curve_arr)
    drawdowns   = (curve_arr - rolling_max) / (rolling_max + 1e-9)
    max_drawdown = float(drawdowns.min()) * 100

    # Thin curve to last 252 points for UI performance
    thin  = max(1, len(curve_dates) // 252)
    thin_dates  = curve_dates[::thin]
    thin_curve  = curve_values[::thin]
    thin_market = market_curve[::thin]

    return {
        "ticker":               ticker_name,
        "yf_symbol":            yf_symbol,
        "market_return_pct":    round(market_return, 2),
        "strategy_return_pct":  round(strategy_return, 2),
        "outperformance_pct":   round(outperformance, 2),
        "sharpe_ratio":         round(sharpe, 2),
        "max_drawdown_pct":     round(max_drawdown, 2),
        "win_rate_pct":         round(win_rate, 2),
        "num_trades":           num_trades,
        "num_wins":             len(wins),
        "num_losses":           len(losses),
        "trade_log":            trade_log[-50:],  # last 50 trades
        "portfolio_curve": {
            "dates":    thin_dates,
            "strategy": thin_curve,
            "market":   thin_market,
            "buy_dates":  buy_dates,
            "sell_dates": sell_dates,
        },
    }


def clear_cache():
    global __model_cache
    __model_cache = {}
