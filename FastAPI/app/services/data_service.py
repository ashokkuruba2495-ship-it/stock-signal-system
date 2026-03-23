import pandas as pd
import numpy as np
import yfinance as yf
import warnings
import tempfile
import os
from app.core.config import logger

# yfinance internally caches timezone data using SQLite.
# Point the cache to the system temp dir (always a valid path) so
# yfinance never receives None as a directory, which caused:
# "TypeError: _path_isdir: path should be string ... not NoneType"
try:
    _tz_cache = os.path.join(tempfile.gettempdir(), "yfinance_tz_cache")
    os.makedirs(_tz_cache, exist_ok=True)
    yf.set_tz_cache_location(_tz_cache)
except Exception:
    pass  # If this API is unavailable in the installed version, skip silently

# Suppress residual ResourceWarning from yfinance / requests_cache
warnings.filterwarnings("ignore", category=ResourceWarning)


def fetch_stock_data(symbol: str) -> pd.DataFrame:
    try:
        # Requesting 5 years natively to guarantee rolling(252) works seamlessly without dropping modern days
        df = yf.download(symbol, period="5y", progress=False)
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        raise ValueError(f"Failed to fetch data from Yahoo Finance for {symbol}")

    if df is None or df.empty:
        raise ValueError(f"No data returned for symbol: {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        raise ValueError("Required column 'Close' not found in data")

    df = df.reset_index()
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Empty DataFrame received for cleaning")
    df = df.copy()
    df.drop_duplicates(inplace=True)
    df.ffill(inplace=True)
    if "Date" in df.columns:
        df.sort_values("Date", inplace=True)
    return df

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Basic feature set for simple visualization charts."""
    if df.empty:
        raise ValueError("Empty DataFrame received for feature creation")

    df = df.copy()
    df["Return"] = df["Close"].pct_change()
    df["MA20"]   = df["Close"].rolling(window=20).mean()
    df["MA50"]   = df["Close"].rolling(window=50).mean()
    df["Volatility"] = df["Return"].rolling(window=20).std()
    df["Volume_Change"] = df["Volume"].pct_change()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    df.dropna(inplace=True)
    return df

def compute_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """Advanced 50+ feature set matching train_models.py"""
    df = df.copy()
    c, h, l, o, v = df["Close"], df["High"], df["Low"], df["Open"], df["Volume"]

    for p in [5, 10, 20, 50, 100, 200]:
        df[f"SMA_{p}"] = c.rolling(p).mean()
    for p in [5, 9, 12, 21, 26]:
        df[f"EMA_{p}"] = c.ewm(span=p, adjust=False).mean()

    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]

    for p in [10, 20, 50]:
        df[f"dist_SMA{p}"] = (c - df[f"SMA_{p}"]) / (df[f"SMA_{p}"] + 1e-9)

    df["SMA5_10"]  = df["SMA_5"]  - df["SMA_10"]
    df["SMA10_20"] = df["SMA_10"] - df["SMA_20"]
    df["SMA20_50"] = df["SMA_20"] - df["SMA_50"]
    df["EMA9_21"]  = df["EMA_9"]  - df["EMA_21"]

    delta = c.diff()
    for period in [7, 14, 21]:
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs   = gain / (loss + 1e-9)
        df[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    df["RSI_oversold"]   = (df["RSI_14"] < 30).astype(int)
    df["RSI_overbought"] = (df["RSI_14"] > 70).astype(int)

    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    df["Stoch_K"]     = 100 * (c - low14) / (high14 - low14 + 1e-9)
    df["Stoch_D"]     = df["Stoch_K"].rolling(3).mean()
    df["Stoch_cross"] = (df["Stoch_K"] > df["Stoch_D"]).astype(int)
    df["Williams_R"]  = -100 * (high14 - c) / (high14 - low14 + 1e-9)

    for p in [5, 10, 20]:
        df[f"ROC_{p}"] = c.pct_change(p) * 100
    df["MOM_10"] = c - c.shift(10)
    df["MOM_20"] = c - c.shift(20)

    for p in [10, 20]:
        mid = c.rolling(p).mean()
        std = c.rolling(p).std()
        df[f"BB_upper_{p}"] = mid + 2 * std
        df[f"BB_lower_{p}"] = mid - 2 * std
        df[f"BB_width_{p}"] = (df[f"BB_upper_{p}"] - df[f"BB_lower_{p}"]) / (mid + 1e-9)
        df[f"BB_pct_{p}"]   = (c - df[f"BB_lower_{p}"]) / (df[f"BB_upper_{p}"] - df[f"BB_lower_{p}"] + 1e-9)

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR_14"]    = tr.rolling(14).mean()
    df["ATR_ratio"] = df["ATR_14"] / (c + 1e-9)
    df["HV_10"]     = c.pct_change().rolling(10).std() * np.sqrt(252)
    df["HV_20"]     = c.pct_change().rolling(20).std() * np.sqrt(252)

    df["Vol_SMA10"] = v.rolling(10).mean()
    df["Vol_SMA20"] = v.rolling(20).mean()
    df["Vol_ratio"] = v / (df["Vol_SMA10"] + 1e-9)
    df["Vol_trend"] = df["Vol_SMA10"] / (df["Vol_SMA20"] + 1e-9)

    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    df["OBV_signal"] = (obv > obv.rolling(10).mean()).astype(int)

    for p in [1, 2, 3, 5, 10, 20]:
        df[f"Ret_{p}d"] = c.pct_change(p)
    df["HL_ratio"] = (h - l) / (c + 1e-9)
    df["CO_ratio"] = (c - o) / (o + 1e-9)
    df["Gap"]      = (o - c.shift()) / (c.shift() + 1e-9)

    df["Doji"]          = (abs(c - o) / (h - l + 1e-9) < 0.1).astype(int)
    df["Hammer"]        = ((c > o) & ((o - l) > 2 * (c - o))).astype(int)
    df["Shooting_star"] = ((o > c) & ((h - o) > 2 * (o - c))).astype(int)

    df["Trend_up"]     = (df["SMA_10"] > df["SMA_20"]).astype(int)
    df["Above_SMA50"]  = (c > df["SMA_50"]).astype(int)
    df["Above_SMA200"] = (c > df["SMA_200"]).astype(int)
    df["Golden_cross"] = (df["SMA_50"] > df["SMA_200"]).astype(int)

    df["High_52w"] = h.rolling(252).max()
    df["Low_52w"]  = l.rolling(252).min()
    df["Pct_52w"]  = (c - df["Low_52w"]) / (df["High_52w"] - df["Low_52w"] + 1e-9)

    for lag in [1, 2, 3, 5]:
        df[f"RSI_lag{lag}"]  = df["RSI_14"].shift(lag)
        df[f"MACD_lag{lag}"] = df["MACD"].shift(lag)
        df[f"Ret_lag{lag}"]  = df["Ret_1d"].shift(lag)

    df.dropna(inplace=True)
    return df
