import numpy as np
import pandas as pd

FEATURE_COLS = [
    "ret",
    "ret_lag1",
    "ret_lag2",
    "ret_lag3",
    "ret_lag5",
    "ma5",
    "ma10",
    "ma20",
    "close_over_ma5",
    "close_over_ma10",
    "close_over_ma20",
    "rsi14",
    "macd",
    "macd_signal",
    "macd_hist",
    "volume_ratio",
    "position20",
    "amplitude",
    "turnover",
    "pct_change",
]


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    return dif, dea, hist


def add_features(df):
    out = df.copy()
    close = out["close"]
    volume = out["volume"]

    out["ret"] = close.pct_change()
    for lag in (1, 2, 3, 5):
        out[f"ret_lag{lag}"] = out["ret"].shift(lag)

    for window in (5, 10, 20):
        ma = close.rolling(window).mean()
        out[f"ma{window}"] = ma
        out[f"close_over_ma{window}"] = close / ma - 1

    out["rsi14"] = _rsi(close)
    out["macd"], out["macd_signal"], out["macd_hist"] = _macd(close)
    out["volume_ratio"] = volume / volume.rolling(5).mean()

    out["rolling_min20"] = close.rolling(20).min()
    out["rolling_max20"] = close.rolling(20).max()
    out["position20"] = (close - out["rolling_min20"]) / (
        out["rolling_max20"] - out["rolling_min20"]
    )

    return out


def build_label(df, horizon):
    close = df["close"]
    future_close = close.shift(-horizon)
    return (future_close > close).astype(int)
