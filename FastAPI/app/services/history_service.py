"""
In-memory signal history service.
Records live signals with timestamps so the History page can display them.
"""
from collections import deque
from datetime import datetime
from typing import List, Dict

# Max number of entries kept per ticker in memory
_MAX_HISTORY = 200

# { ticker -> deque of {timestamp, signal, price, confidence_pct, buy_prob, sell_prob, trend} }
_history: Dict[str, deque] = {}


def record_signal(
    ticker: str,
    signal: str,
    price: float,
    confidence_pct: float,
    buy_prob: float,
    sell_prob: float,
    trend: str = "→",
) -> None:
    if ticker not in _history:
        _history[ticker] = deque(maxlen=_MAX_HISTORY)
    _history[ticker].appendleft({
        "ticker": ticker,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal": signal,
        "price": price,
        "confidence_pct": round(confidence_pct, 1),
        "buy_prob": round(buy_prob, 4),
        "sell_prob": round(sell_prob, 4),
        "trend": trend,
    })


def get_history(ticker: str, limit: int = 50) -> List[dict]:
    buf = _history.get(ticker, deque())
    return list(buf)[:limit]


def get_all_latest(limit_per_ticker: int = 5) -> List[dict]:
    result = []
    for ticker, buf in _history.items():
        result.extend(list(buf)[:limit_per_ticker])
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return result


def get_tickers_with_history() -> List[str]:
    return [t for t, buf in _history.items() if len(buf) > 0]
