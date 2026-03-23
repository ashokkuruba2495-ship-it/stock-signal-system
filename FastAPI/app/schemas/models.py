from pydantic import BaseModel
from typing import Dict, Optional, List, Any

class ThresholdUpdate(BaseModel):
    thresholds: Dict[str, float]

class RecipientUpdate(BaseModel):
    email: str

class SignalProbability(BaseModel):
    BUY: float
    HOLD: float
    SELL: float

class SignalResponse(BaseModel):
    ticker: str
    yf_symbol: str
    signal: str
    confidence: Optional[str] = None
    confidence_pct: Optional[float] = None
    trend: Optional[str] = None
    buy_prob: Optional[float] = None
    sell_prob: Optional[float] = None
    probabilities: SignalProbability
    price: Optional[float] = None
    model_type: Optional[str] = None
    cv_accuracy: Optional[float] = None
    test_accuracy: Optional[float] = None
    trained_at: Optional[str] = None
    sector: Optional[str] = None
    error: Optional[str] = None

class TradeEntry(BaseModel):
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    result: str

class PortfolioCurve(BaseModel):
    dates: List[str]
    strategy: List[float]
    market: List[float]
    buy_dates: List[str]
    sell_dates: List[str]

class BacktestResponse(BaseModel):
    ticker: str
    yf_symbol: str
    market_return_pct: float
    strategy_return_pct: float
    outperformance_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    num_trades: int
    num_wins: int
    num_losses: int
    trade_log: List[TradeEntry]
    portfolio_curve: PortfolioCurve

class SignalHistoryEntry(BaseModel):
    ticker: str
    timestamp: str
    signal: str
    price: float
    confidence_pct: float
    buy_prob: float
    sell_prob: float
    trend: str
