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
    "pct_change",
]


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    eps = 1e-12
    flat = (avg_loss.le(eps)) & (avg_gain.le(eps))
    up_only = (avg_loss.le(eps)) & (avg_gain.gt(eps))
    rsi = rsi.mask(flat, 50.0).mask(up_only, 100.0)
    return rsi


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

    # 上游若未提供振幅/涨跌幅（如腾讯只有 OHLCV），由 OHLCV 补算，口径与 akshare 一致
    if "amplitude" not in out.columns:
        prev_close = close.shift(1)
        out["amplitude"] = (out["high"] - out["low"]) / prev_close * 100
    if "pct_change" not in out.columns:
        out["pct_change"] = out["ret"] * 100

    out["rolling_min20"] = close.rolling(20).min()
    out["rolling_max20"] = close.rolling(20).max()
    out["position20"] = (close - out["rolling_min20"]) / (
        out["rolling_max20"] - out["rolling_min20"]
    )

    return out


def build_label(df, horizon, threshold=0.0):
    close = df["close"]
    future_close = close.shift(-horizon)
    if threshold <= 0:
        label = (future_close > close).astype(float)
        label[future_close.isna()] = np.nan
        return label
    move = (future_close - close) / close
    label = pd.Series(np.nan, index=df.index, dtype="float")
    label[move > threshold] = 1.0
    label[move < -threshold] = 0.0
    return label
