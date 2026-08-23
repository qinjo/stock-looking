import os

import akshare as ak
import pandas as pd

from . import config

_COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "换手率": "turnover",
}


def _cache_path(symbol, start_date, end_date, adjust):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    name = f"{symbol}_{start_date}_{end_date}_{adjust}.csv"
    return os.path.join(config.CACHE_DIR, name)


def _load_cached(symbol, start_date, end_date, adjust):
    path = _cache_path(symbol, start_date, end_date, adjust)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def fetch_history(symbol, start_date, end_date, adjust="qfq"):
    cached = _load_cached(symbol, start_date, end_date, adjust)
    if cached is not None:
        cached["date"] = pd.to_datetime(cached["date"])
        return cached

    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    except Exception as exc:
        raise RuntimeError(
            f"拉取 {symbol} ({start_date}~{end_date}) 失败：{type(exc).__name__}: {exc}。"
            "可能的网络/反爬原因：请直连 eastmoney 或在代理里放行其域名；"
            "确认网络可用后重试。"
        ) from exc

    if df is None or df.empty:
        raise ValueError(
            f"{symbol} ({start_date}~{end_date}) 返回空数据，请检查股票代码或日期范围。"
        )

    df = df.rename(columns=_COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(_cache_path(symbol, start_date, end_date, adjust), index=False)
    return df
