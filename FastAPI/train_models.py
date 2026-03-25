"""
Advanced ML Training Script — Top 10 NSE Stocks
Target: 80%+ accuracy using ensemble stacking, feature selection,
        advanced indicators, and hyperparameter tuning.
"""

import os, pickle, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ── ML Models ──────────────────────────────────────────────────────────────────
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier, StackingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.feature_selection import SelectFromModel
from sklearn.metrics import accuracy_score, classification_report

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[INFO] XGBoost not installed. Run: pip install xgboost")

try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("[INFO] LightGBM not installed. Run: pip install lightgbm")

warnings.filterwarnings("ignore")

# ── Config ─────────────────────────────────────────────────────────────────────
TOP_10_STOCKS = {
    "RELIANCE":    "RELIANCE.NS",
    "TCS":         "TCS.NS",
    "HDFCBANK":    "HDFCBANK.NS",
    "INFY":        "INFY.NS",
    "ICICIBANK":   "ICICIBANK.NS",
    "HINDUNILVR":  "HINDUNILVR.NS",
    "ITC":         "ITC.NS",
    "SBIN":        "SBIN.NS",
    "BHARTIARTL":  "BHARTIARTL.NS",
    "KOTAKBANK":   "KOTAKBANK.NS",
}
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

HORIZON   = 5      # predict 5-day forward return
THRESHOLD = 0.015  # 1.5% move = BUY/SELL
N_SPLITS  = 5      # TimeSeriesSplit folds


# ══════════════════════════════════════════════════════════════════════════════
# 1. ADVANCED FEATURE ENGINEERING  (50+ features)
# ══════════════════════════════════════════════════════════════════════════════
def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    o = df["Open"]
    v = df["Volume"]

    # ── Trend: Moving Averages ─────────────────────────────────────────────────
    for p in [5, 10, 20, 50, 100, 200]:
        df[f"SMA_{p}"] = c.rolling(p).mean()
    for p in [5, 9, 12, 21, 26]:
        df[f"EMA_{p}"] = c.ewm(span=p, adjust=False).mean()

    df["MACD"]        = df["EMA_12"] - df["EMA_26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]

    # Price distance from MAs
    for p in [10, 20, 50]:
        df[f"dist_SMA{p}"] = (c - df[f"SMA_{p}"]) / (df[f"SMA_{p}"] + 1e-9)

    # MA crossover strengths
    df["SMA5_10"]    = df["SMA_5"]  - df["SMA_10"]
    df["SMA10_20"]   = df["SMA_10"] - df["SMA_20"]
    df["SMA20_50"]   = df["SMA_20"] - df["SMA_50"]
    df["EMA9_21"]    = df["EMA_9"]  - df["EMA_21"]

    # ── Momentum ───────────────────────────────────────────────────────────────
    delta = c.diff()
    for period in [7, 14, 21]:
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs   = gain / (loss + 1e-9)
        df[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    df["RSI_oversold"]   = (df["RSI_14"] < 30).astype(int)
    df["RSI_overbought"] = (df["RSI_14"] > 70).astype(int)

    # Stochastic
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    df["Stoch_K"]    = 100 * (c - low14) / (high14 - low14 + 1e-9)
    df["Stoch_D"]    = df["Stoch_K"].rolling(3).mean()
    df["Stoch_cross"]= (df["Stoch_K"] > df["Stoch_D"]).astype(int)

    # Williams %R
    df["Williams_R"] = -100 * (high14 - c) / (high14 - low14 + 1e-9)

    # Rate of Change
    for p in [5, 10, 20]:
        df[f"ROC_{p}"] = c.pct_change(p) * 100

    df["MOM_10"] = c - c.shift(10)
    df["MOM_20"] = c - c.shift(20)

    # ── Volatility ─────────────────────────────────────────────────────────────
    for p in [10, 20]:
        mid = c.rolling(p).mean()
        std = c.rolling(p).std()
        df[f"BB_upper_{p}"] = mid + 2 * std
        df[f"BB_lower_{p}"] = mid - 2 * std
        df[f"BB_width_{p}"] = (df[f"BB_upper_{p}"] - df[f"BB_lower_{p}"]) / (mid + 1e-9)
        df[f"BB_pct_{p}"]   = (c - df[f"BB_lower_{p}"]) / (df[f"BB_upper_{p}"] - df[f"BB_lower_{p}"] + 1e-9)

    # ATR
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR_14"]    = tr.rolling(14).mean()
    df["ATR_ratio"] = df["ATR_14"] / (c + 1e-9)

    # Historical Volatility
    df["HV_10"] = c.pct_change().rolling(10).std() * np.sqrt(252)
    df["HV_20"] = c.pct_change().rolling(20).std() * np.sqrt(252)

    # ── Volume ─────────────────────────────────────────────────────────────────
    df["Vol_SMA10"]   = v.rolling(10).mean()
    df["Vol_SMA20"]   = v.rolling(20).mean()
    df["Vol_ratio"]   = v / (df["Vol_SMA10"] + 1e-9)
    df["Vol_trend"]   = df["Vol_SMA10"] / (df["Vol_SMA20"] + 1e-9)

    # OBV
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    df["OBV_signal"] = (obv > obv.rolling(10).mean()).astype(int)

    # ── Price Action ───────────────────────────────────────────────────────────
    for p in [1, 2, 3, 5, 10, 20]:
        df[f"Ret_{p}d"] = c.pct_change(p)

    df["HL_ratio"]  = (h - l) / (c + 1e-9)
    df["CO_ratio"]  = (c - o) / (o + 1e-9)
    df["Gap"]       = (o - c.shift()) / (c.shift() + 1e-9)

    # Candlestick patterns
    df["Doji"]         = (abs(c - o) / (h - l + 1e-9) < 0.1).astype(int)
    df["Hammer"]       = ((c > o) & ((o - l) > 2*(c - o))).astype(int)
    df["Shooting_star"]= ((o > c) & ((h - o) > 2*(o - c))).astype(int)

    # ── Regime ─────────────────────────────────────────────────────────────────
    df["Trend_up"]     = (df["SMA_10"] > df["SMA_20"]).astype(int)
    df["Above_SMA50"]  = (c > df["SMA_50"]).astype(int)
    df["Above_SMA200"] = (c > df["SMA_200"]).astype(int)
    df["Golden_cross"] = (df["SMA_50"] > df["SMA_200"]).astype(int)

    # 52-week position
    df["High_52w"]     = h.rolling(252).max()
    df["Low_52w"]      = l.rolling(252).min()
    df["Pct_52w"]      = (c - df["Low_52w"]) / (df["High_52w"] - df["Low_52w"] + 1e-9)

    # ── Lagged features ────────────────────────────────────────────────────────
    for lag in [1, 2, 3, 5]:
        df[f"RSI_lag{lag}"]  = df["RSI_14"].shift(lag)
        df[f"MACD_lag{lag}"] = df["MACD"].shift(lag)
        df[f"Ret_lag{lag}"]  = df["Ret_1d"].shift(lag)

    return df


def get_feature_cols(df: pd.DataFrame) -> list:
    exclude = {"Open","High","Low","Close","Volume","Label","High_52w","Low_52w"}
    return [col for col in df.columns if col not in exclude and df[col].dtype != object]


# ══════════════════════════════════════════════════════════════════════════════
# 2. ADAPTIVE LABEL CREATION
# ══════════════════════════════════════════════════════════════════════════════
def create_labels(df: pd.DataFrame) -> pd.Series:
    fwd = df["Close"].pct_change(HORIZON).shift(-HORIZON)
    atr = df["ATR_ratio"].fillna(THRESHOLD)
    thr = np.maximum(atr * 1.5, THRESHOLD)   # adaptive per-row threshold
    labels = pd.Series(1, index=df.index)
    labels[fwd >  thr] = 2   # BUY
    labels[fwd < -thr] = 0   # SELL
    return labels


# ══════════════════════════════════════════════════════════════════════════════
# 3. BUILD BASE MODELS
# ══════════════════════════════════════════════════════════════════════════════
def build_base_models() -> dict:
    models = {
        "RF": RandomForestClassifier(
            n_estimators=100, max_depth=12, min_samples_leaf=2,
            max_features="sqrt", class_weight="balanced",
            random_state=42, n_jobs=-1,
        ),
        "ET": ExtraTreesClassifier(
            n_estimators=100, max_depth=12, min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
        "GB": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=5,
            subsample=0.8, min_samples_leaf=3, random_state=42,
        ),
    }
    if HAS_XGB:
        models["XGB"] = XGBClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="mlogloss", random_state=42, n_jobs=-1,
        )
    if HAS_LGB:
        models["LGB"] = LGBMClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=6,
            num_leaves=63, subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1,
        )
    return models


# ══════════════════════════════════════════════════════════════════════════════
# 4. ROBUST DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
def robust_download(symbol: str, start, end) -> pd.DataFrame:
    """Try multiple strategies to handle NoneType / timezone / rate-limit errors."""

    # Strategy 1: standard
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if df is not None and not df.empty and len(df) > 100:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            return df
    except Exception as e:
        print(f"    [S1 failed] {e}")

    # Strategy 2: no auto_adjust
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
        if df is not None and not df.empty and len(df) > 100:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df[["Open","High","Low","Close","Volume"]].copy()
            return df
    except Exception as e:
        print(f"    [S2 failed] {e}")

    # Strategy 3: Ticker.history()
    try:
        t  = yf.Ticker(symbol)
        df = t.history(start=start, end=end, auto_adjust=True)
        if df is not None and not df.empty and len(df) > 100:
            df = df[["Open","High","Low","Close","Volume"]].copy()
            return df
    except Exception as e:
        print(f"    [S3 failed] {e}")

    # Strategy 4: period string
    try:
        df = yf.download(symbol, period="5y", progress=False, auto_adjust=True)
        if df is not None and not df.empty and len(df) > 100:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            return df
    except Exception as e:
        print(f"    [S4 failed] {e}")

    # Strategy 5: Ticker period
    try:
        t  = yf.Ticker(symbol)
        df = t.history(period="5y", auto_adjust=True)
        if df is not None and not df.empty and len(df) > 100:
            df = df[["Open","High","Low","Close","Volume"]].copy()
            return df
    except Exception as e:
        print(f"    [S5 failed] {e}")

    print(f"    [ERROR] All download strategies failed for {symbol}")
    return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# 5. TRAIN SINGLE STOCK
# ══════════════════════════════════════════════════════════════════════════════
def train_stock(ticker_name: str, ticker_symbol: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  {ticker_name} ({ticker_symbol})")
    print(f"{'='*60}")

    # 5 years of data — robust multi-strategy download
    end   = datetime.today()
    start = end - timedelta(days=5 * 365)
    print(f"  Downloading data...")
    raw   = robust_download(ticker_symbol, start, end)
    if raw is None or raw.empty or len(raw) < 200:
        print(f"  [WARN] Insufficient data after all retries. Skipping.")
        return {}

    df = compute_features(raw)
    df["Label"] = create_labels(df)
    df.dropna(inplace=True)

    feat_cols = get_feature_cols(df)
    X = df[feat_cols].values
    y = df["Label"].values.astype(int)

    print(f"  Samples: {len(X)} | Features: {len(feat_cols)}")
    print(f"  Labels → BUY:{(y==2).sum()}  HOLD:{(y==1).sum()}  SELL:{(y==0).sum()}")

    # ── Scale ──────────────────────────────────────────────────────────────────
    scaler   = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Feature selection ──────────────────────────────────────────────────────
    rf_sel = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf_sel.fit(X_scaled, y)
    selector  = SelectFromModel(rf_sel, threshold="median", prefit=True)
    X_sel     = selector.transform(X_scaled)
    sel_feats = [feat_cols[i] for i, m in enumerate(selector.get_support()) if m]
    print(f"  Selected {len(sel_feats)} features after selection")

    # ── Cross-validation on individual models ──────────────────────────────────
    tscv       = TimeSeriesSplit(n_splits=N_SPLITS)
    base_models= build_base_models()
    cv_results = {}

    print("\n  Cross-Validation (TimeSeriesSplit):")
    for name, model in base_models.items():
        scores = cross_val_score(model, X_sel, y, cv=tscv,
                                 scoring="accuracy", n_jobs=-1)
        cv_results[name] = scores.mean()
        print(f"    {name:<5}: {scores.mean():.4f} ± {scores.std():.4f}")

    # ── Stacking ensemble ──────────────────────────────────────────────────────
    print("  Training Stacking Ensemble...")
    stack = StackingClassifier(
        estimators=[(n, m) for n, m in base_models.items()],
        final_estimator=LogisticRegression(C=1.0, max_iter=1000, random_state=42),
        cv=3, stack_method="predict_proba", n_jobs=1,
    )
    stack_scores = cross_val_score(stack, X_sel, y, cv=tscv,
                                   scoring="accuracy", n_jobs=1)
    stack_mean   = stack_scores.mean()
    cv_results["STACK"] = stack_mean
    print(f"    STACK: {stack_mean:.4f} ± {stack_scores.std():.4f}")

    # ── Pick best ──────────────────────────────────────────────────────────────
    best_name   = max(cv_results, key=cv_results.get)
    best_cv_acc = cv_results[best_name]
    print(f"\n  ✓ Best: {best_name}  (CV={best_cv_acc:.4f})")

    # ── Final train + hold-out test ────────────────────────────────────────────
    split    = int(len(X_sel) * 0.8)
    X_tr, X_te = X_sel[:split], X_sel[split:]
    y_tr, y_te = y[:split],     y[split:]

    if best_name == "STACK":
        final = StackingClassifier(
            estimators=[(n, m) for n, m in build_base_models().items()],
            final_estimator=LogisticRegression(C=1.0, max_iter=1000, random_state=42),
            cv=3, stack_method="predict_proba", n_jobs=1,
        )
    else:
        final = build_base_models()[best_name]

    final.fit(X_tr, y_tr)
    test_acc = accuracy_score(y_te, final.predict(X_te))
    print(f"  Hold-out accuracy : {test_acc:.4f}")
    print(classification_report(y_te, final.predict(X_te),
                                  target_names=["SELL","HOLD","BUY"],
                                  zero_division=0))

    # ── Latest signal ──────────────────────────────────────────────────────────
    latest_s = scaler.transform(df[feat_cols].iloc[[-1]].values)
    latest_x = selector.transform(latest_s)
    proba    = final.predict_proba(latest_x)[0]
    cls      = final.predict(latest_x)[0]
    sig_map  = {0:"SELL", 1:"HOLD", 2:"BUY"}

    payload = {
        # identifiers
        "ticker_name":       ticker_name,
        "ticker_symbol":     ticker_symbol,
        # model artifacts
        "model":             final,
        "model_type":        best_name,
        "scaler":            scaler,
        "selector":          selector,
        "feature_cols":      feat_cols,
        "selected_features": sel_feats,
        # metrics
        "accuracy":          round(test_acc, 4),
        "cv_accuracy":       round(best_cv_acc, 4),
        "test_accuracy":     round(test_acc, 4),
        "cv_results":        {k: round(v, 4) for k, v in cv_results.items()},
        "train_samples":     split,
        "test_samples":      len(X_te),
        # signal
        "trained_at":        datetime.now().isoformat(),
        "latest_signal":     sig_map[int(cls)],
        "signal_proba": {
            "SELL": round(float(proba[0]), 4),
            "HOLD": round(float(proba[1]), 4),
            "BUY":  round(float(proba[2]), 4),
        },
        "latest_close":      round(float(df["Close"].iloc[-1]), 2),
        "latest_date":       str(df.index[-1].date()),
        "label_distribution":{
            "SELL": int((y==0).sum()),
            "HOLD": int((y==1).sum()),
            "BUY":  int((y==2).sum()),
        },
    }

    pkl_path = os.path.join(MODELS_DIR, f"{ticker_name}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(payload, f)

    print(f"\n  ✓ Saved → {pkl_path}")
    print(f"  Signal: {sig_map[int(cls)]}  "
          f"(BUY={proba[2]:.1%}  HOLD={proba[1]:.1%}  SELL={proba[0]:.1%})")
    return payload


# ══════════════════════════════════════════════════════════════════════════════
# 5. TRAIN ALL 10
# ══════════════════════════════════════════════════════════════════════════════
def train_all():
    print("\n" + "█"*60)
    print("  AI STOCK SIGNAL — ADVANCED ENSEMBLE TRAINING")
    print("  Top 10 NSE | Stacking | 50+ Features | TimeSeriesCV")
    print("█"*60)
    if HAS_XGB: print("  ✓ XGBoost available")
    if HAS_LGB: print("  ✓ LightGBM available")
    if not HAS_XGB and not HAS_LGB:
        print("  ⚠  Install for best results:")
        print("     pip install xgboost lightgbm")

    results = {}
    for name, symbol in TOP_10_STOCKS.items():
        try:
            results[name] = train_stock(name, symbol)
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "═"*60)
    print(f"  {'STOCK':<14} {'MODEL':<8} {'CV':>6} {'TEST':>6}  SIGNAL")
    print("═"*60)
    accs = []
    for name, res in results.items():
        if res:
            acc = res.get("test_accuracy", 0)
            accs.append(acc)
            flag = "🟢" if acc >= 0.80 else "🟡" if acc >= 0.70 else "🔴"
            print(f"  {name:<14} {res.get('model_type',''):<8} "
                  f"{res.get('cv_accuracy',0):>5.1%}  {acc:>5.1%}  "
                  f"{res.get('latest_signal','')}  {flag}")
    if accs:
        print("═"*60)
        print(f"  Average test accuracy: {np.mean(accs):.1%}")
        print(f"  Models ≥80%: {sum(1 for a in accs if a>=0.80)}/10")
    print(f"\n  Pickle files saved to: {MODELS_DIR}\n")


if __name__ == "__main__":
    train_all()
