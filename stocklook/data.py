import os
import time

import pandas as pd
import requests

from . import config

_BASE = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_PAGE = 640  # 腾讯单次请求最多返回的日线条数

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}


def tencent_symbol(symbol):
    """600519 -> sh600519；000001/300750 -> sz000001 / sz300750；8/4 开头 -> bj。"""
    if symbol.startswith(("6", "9")):
        return f"sh{symbol}"
    if symbol.startswith(("0", "2", "3")):
        return f"sz{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    raise ValueError(f"无法识别股票代码前缀：{symbol}")


def parse_tencent_kline(payload):
    """把腾讯 fqkline 接口的 JSON 解析为规范日线 DataFrame（纯函数，不碰网络）。

    payload 形如 {"data": {"sh600519": {"qfqday": [[date, open, close, high, low, volume], ...]}}}
    正常返回列：date / open / close / high / low / volume，按日期升序。
    复权数据在 "qfqday"（前复权）或 "day"（不复权）键下。
    """
    data = payload.get("data") or {}
    node = next(iter(data.values())) if data else {}
    rows = node.get("qfqday") or node.get("day") or node.get("hfqday")
    if not rows:
        raise ValueError("腾讯接口返回数据为空或格式异常")
    # 除权除息日的行会附带分红信息 dict（第 7 字段），只取前 6 列 OHLCV
    rows = [row[:6] for row in rows if len(row) >= 6]
    df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume"])
    for col in ("open", "close", "high", "low", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    return df[["date", "open", "close", "high", "low", "volume"]]


def merge_pages(pages):
    """多页日线 DataFrame 合并：按日期去重、升序排序。"""
    if not pages:
        raise ValueError("未拉到任何日线数据")
    df = pd.concat(pages, ignore_index=True).drop_duplicates(subset="date")
    return df.sort_values("date").reset_index(drop=True)


def _request_kline(symbol, adjust, start, end, count=_PAGE):
    """向腾讯发起一次分页请求，返回原始 JSON（带一次重试）。"""
    params = {"param": f"{symbol},day,{start},{end},{count},{adjust}"}
    resp = None
    for session in (_direct_session, _default_session):
        try:
            resp = session.get(_BASE, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            continue
    assert resp is not None
    raise resp.raise_for_status()


# macOS 上 requests 默认读系统代理（trust_env），腾讯接口需直连；
# 若直连不通则回退到系统代理，兼顾必须先走代理的网络环境。
_direct_session = requests.Session()
_direct_session.trust_env = False
_direct_session.headers.update(_HEADERS)

_default_session = requests.Session()
_default_session.headers.update(_HEADERS)


def _cache_path(symbol, start_date, end_date, adjust):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    name = f"tx_{symbol}_{start_date}_{end_date}_{adjust}.csv"
    return os.path.join(config.CACHE_DIR, name)


def _load_cached(symbol, start_date, end_date, adjust):
    path = _cache_path(symbol, start_date, end_date, adjust)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def fetch_history(symbol, start_date, end_date, adjust="qfq", _http_get=None):
    """拉取指定股票历史日线（腾讯接口，前复权）。签名与原 akshare 版保持一致。

    start_date / end_date 格式 "20150101"；返回按日期升序的 DataFrame：
    date / open / close / high / low / volume。
    """
    cached = _load_cached(symbol, start_date, end_date, adjust)
    if cached is not None:
        cached["date"] = pd.to_datetime(cached["date"])
        return cached

    ts_symbol = tencent_symbol(symbol)
    start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    http_get = _http_get or _request_kline

    # 腾讯接口按「end 往前最近的 count 条」返回，故从 end 向 start 翻页
    page_end = end
    pages = []
    try:
        for _ in range(200):  # 防御性上限：约 200 页 = 12.8 万条
            payload = http_get(ts_symbol, adjust, start, page_end)
            df = parse_tencent_kline(payload)
            if df.empty:
                break
            first_date = df["date"].iloc[0]
            pages.append(df)
            if len(df) < _PAGE or str(first_date.date()) <= start:
                break
            page_end = (first_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            time.sleep(0.3)  # 轻微限速，避免触发反爬
    except requests.RequestException as exc:
        raise RuntimeError(
            f"拉取 {symbol} ({start_date}~{end_date}) 失败：{type(exc).__name__}: {exc}。"
            "腾讯接口不可达（网络/反爬），请确认网络后重试。"
        ) from exc

    df = merge_pages(pages)
    if df.empty:
        raise ValueError(
            f"{symbol} ({start_date}~{end_date}) 返回空数据，请检查股票代码或日期范围。"
        )
    df.to_csv(_cache_path(symbol, start_date, end_date, adjust), index=False)
    return df