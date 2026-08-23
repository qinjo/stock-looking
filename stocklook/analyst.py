"""实时行情快照 + DeepSeek 大模型分析。

纯函数 seam（可离线测试）：
- parse_tencent_quote : 腾讯实时快照文本 -> 规整 dict
- build_analysis_prompt : 快照 + 近期走势 + 指标 + 回测 -> prompt 字符串
- parse_llm_json : 模型回复 -> JSON dict（容错代码块/杂文）

网络 seam（注入式可测）：
- call_deepseek : 调 DeepSeek chat/completions（直连优先，代理兜底）

关键安全约束：API key 只作为参数传入（CLI 从环境变量 DEEPSEEK_API_KEY
或 --api-key 读取），绝不写入代码、配置文件或序列化进结果。
"""
import json
import re
import time
from datetime import datetime

import pandas as pd
import requests

from .data import tencent_symbol

API_URL = "https://api.deepseek.com/chat/completions"
QUOTE_URL = "https://qt.gtimg.cn/q={symbol}"
SINA_QUOTE_URL = "https://hq.sinajs.cn/list={symbol}"
MODEL = "deepseek-chat"
RECENT_DAYS = 30  # prompt 携带的近期交易日条数

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}

# 腾讯实时快照（q=sh600519）字段索引
_F = {
    "name": 1,
    "code": 2,
    "price": 3,
    "prev_close": 4,
    "open": 5,
    "volume": 6,
    "time": 30,
    "change": 31,
    "change_pct": 32,
    "high": 33,
    "low": 34,
    "amount_wan": 37,
    "turnover": 38,
    "amplitude": 43,
    "volume_ratio": 49,
}

_SYSTEM_PROMPT = (
    "你是一名 A 股分析助手。你的任务是基于给定的行情快照和技术指标，"
    "对个股下一个交易日的涨跌方向做一次冷静的概率判断。"
    "务必记住：个股短期方向接近随机，任何预测都不精确，这是参考信号而非承诺。"
    "请给出判断方向、置信度、关键理由和风险提示，不要给出任何买卖操作建议。"
    "只输出 JSON。"
)


def parse_sina_quote(text, code=None):
    """解析新浪实时快照 `hq_str_sh600519="..."`；结构与 parse_tencent_quote 对齐。

    新浪 34 字段版缺换手率/振幅/量比（置 None）；涨跌/涨跌幅由现价与昨收推算。
    """
    match = re.search(r'="([^"]*)"', text or "")
    if not match:
        raise ValueError("新浪快照文本格式异常")
    fields = match.group(1).split(",")
    if len(fields) < 32:
        raise ValueError(f"新浪快照字段不足（仅 {len(fields)} 个）")

    def f(i):
        raw = fields[i].strip()
        try:
            return float(raw) if raw else None
        except ValueError:
            return None

    price, prev_close = f(3), f(2)
    change = price - prev_close if (price is not None and prev_close) else None
    change_pct = change / prev_close * 100 if (change is not None and prev_close) else None
    volume_shares = f(8)  # 股 -> 手
    ts = None
    try:
        ts = datetime.strptime(f"{fields[30]} {fields[31]}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    return {
        "name": fields[0],
        "code": code,
        "price": price,
        "prev_close": prev_close,
        "open": f(1),
        "high": f(4),
        "low": f(5),
        "change": change,
        "change_pct": change_pct,
        "volume": volume_shares / 100 if volume_shares else None,
        "amount_wan": f(9) / 10000 if f(9) else None,
        "turnover": None,
        "amplitude": None,
        "volume_ratio": None,
        "time": ts,
    }


def parse_tencent_quote(text):
    """解析腾讯实时快照文本 `v_sh600519=\"...\"...;` -> 规整 dict（纯函数）。

    数值字段缺失或非法时置 None；多个股票代码同时请求时只解析第一条。
    """
    match = re.search(r'"([^"]*)"', text or "")
    if not match:
        raise ValueError("快照文本格式异常：找不到引号内容")
    fields = match.group(1).split("~")
    if len(fields) <= max(_F.values()):
        raise ValueError(f"快照字段不足（仅 {len(fields)} 个）")

    def num(idx):
        raw = fields[_F[idx]].strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    time_raw = fields[_F["time"]]
    ts = None
    if time_raw and len(time_raw) == 14:
        try:
            ts = datetime.strptime(time_raw, "%Y%m%d%H%M%S")
        except ValueError:
            pass

    return {
        "name": fields[_F["name"]],
        "code": fields[_F["code"]],
        "price": num("price"),
        "prev_close": num("prev_close"),
        "open": num("open"),
        "high": num("high"),
        "low": num("low"),
        "change": num("change"),
        "change_pct": num("change_pct"),
        "volume": num("volume"),
        "amount_wan": num("amount_wan"),
        "turnover": num("turnover"),
        "amplitude": num("amplitude"),
        "volume_ratio": num("volume_ratio"),
        "time": ts,
    }


def parse_quote(text, code=None):
    """自动分派：腾讯快照（~ 分隔）或新浪快照（, 分隔），输出统一结构。"""
    match = re.search(r'"([^"]*)"', text or "")
    body = match.group(1) if match else ""
    if "~" in body:
        return parse_tencent_quote(text)
    return parse_sina_quote(text, code=code)


def build_analysis_prompt(symbol, quote, recent_df, metrics=None, importances=None):
    """把快照 + 近期走势 + 技术指标 + 回测指标拼成 prompt（纯函数）。

    recent_df：已加好特征的最后 RECENT_DAYS 行（含 close/volume/pct_change 等）。
    返回 (system, user) 两个字符串。
    """
    lines = [f"【标的】{quote.get('code') or symbol} {quote.get('name') or ''}".rstrip()]

    t = quote.get("time")
    t_str = t.strftime("%Y-%m-%d %H:%M") if t else "未知"
    lines.append(
        f"【实时快照】时间 {t_str} | 现价 {quote.get('price')} | "
        f"涨跌 {quote.get('change')} ({quote.get('change_pct')}%) | "
        f"今开 {quote.get('open')} | 最高 {quote.get('high')} | 最低 {quote.get('low')} | "
        f"昨收 {quote.get('prev_close')} | 成交量 {quote.get('volume')} 手 | "
        f"成交额 {quote.get('amount_wan')} 万元 | 换手率 {quote.get('turnover')}% | "
        f"振幅 {quote.get('amplitude')}% | 量比 {quote.get('volume_ratio')}"
    )

    lines.append(f"【近{RECENT_DAYS}个交易日走势】(date, close, 涨跌幅%, volume)")
    tail = recent_df.tail(RECENT_DAYS)
    for _, row in tail.iterrows():
        pct = row.get("pct_change")
        if pct is None or pd.isna(pct):
            pct = ""
        else:
            pct = f"{pct:.2f}"
        lines.append(
            f"- {row['date'].strftime('%Y-%m-%d')} {row['close']:.2f} {pct}% {int(row['volume'])}"
        )

    last = tail.iloc[-1]
    ind = last
    lines.append(
        "【今日技术指标】"
        f"ret {ind.get('ret', float('nan')):.4f} | "
        f"MA5 {ind.get('ma5', float('nan')):.2f} | MA10 {ind.get('ma10', float('nan')):.2f} | "
        f"MA20 {ind.get('ma20', float('nan')):.2f} | "
        f"close/MA5 {ind.get('close_over_ma5', float('nan')):.4f} | "
        f"close/MA20 {ind.get('close_over_ma20', float('nan')):.4f} | "
        f"RSI14 {ind.get('rsi14', float('nan')):.1f} | "
        f"MACD DIF {ind.get('macd', float('nan')):.3f} | DEA {ind.get('macd_signal', float('nan')):.3f} | "
        f"hist {ind.get('macd_hist', float('nan')):.3f} | "
        f"量比5日 {ind.get('volume_ratio', float('nan')):.2f} | "
        f"20日位置 {ind.get('position20', float('nan')):.2f}"
    )

    if metrics:
        lines.append(
            "【历史回测参考】过去数年在该股上的 walk-forward 回测（仅供参考，接近随机）："
            f"样本 n={metrics.get('n')}, 上涨基线 up_rate={metrics.get('up_rate', float('nan')):.2f}, "
            f"accuracy={metrics.get('accuracy', float('nan')):.2f}, "
            f"auc={metrics.get('auc', float('nan')):.2f}, "
            f"胜率(预测涨中真涨) win_rate={metrics.get('win_rate', float('nan')):.2f}"
        )

    if importances is not None and not importances.empty:
        top = ", ".join(f"{k}({v:.0f})" for k, v in importances.head(5).items())
        lines.append(f"【模型主要驱动特征】{top}")

    lines.append(
        "【任务】判断该股下一个交易日（T+1）的收盘方向，输出严格 JSON（不要输出 JSON 以外的内容）：\n"
        '{"direction": "up|down|flat", "confidence": 0.0-1.0, '
        '"reasons": ["理由1", "理由2"], "risks": ["风险1"], "summary": "一句话总结"}。'
        "其中 flat 表示方向不明朗（如涨跌幅接近零、多空信号矛盾），"
        "confidence 是你对判断的把握程度。理由要用中文、基于给出的数据。"
    )
    return _SYSTEM_PROMPT, "\n".join(lines)


def parse_llm_json(content):
    """从模型回复提取 JSON -> dict（纯函数）。

    容错：```json 代码块、反引号、回复前后的语气词。
    无法解析时抛 ValueError，由调用方决定保留原文。
    """
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("回复中找不到 JSON")
    return json.loads(text[start : end + 1])


def call_deepseek(prompt, api_key, system=None, _http_post=None):
    """调 DeepSeek chat/completions，返回回复正文（注入式，可离线测试）。"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 900}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    post = _http_post or _post_json
    data = post(API_URL, payload, headers)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"DeepSeek 返回结构异常：{data}") from exc


# macOS 上 requests 默认读系统代理；DeepSeek 直连/代理均可用，直连优先、代理兜底
_direct_session = requests.Session()
_direct_session.trust_env = False
_direct_session.headers.update(_HEADERS)

_default_session = requests.Session()
_default_session.headers.update(_HEADERS)


def _post_json(url, payload, headers):
    resp = None
    for session in (_direct_session, _default_session):
        try:
            resp = session.post(url, json=payload, headers=headers, timeout=60)
            break
        except requests.RequestException:
            continue
    if resp is None:
        raise RuntimeError("DeepSeek 网络请求失败（直连与代理均不可达）")
    if resp.status_code != 200:
        raise RuntimeError(
            f"DeepSeek API 错误 {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def fetch_quote(symbol, _http_get=None):
    """拉取实时行情：优先腾讯快照，限流/失败时自动切换新浪（注入式，可离线测试）。"""
    symbol = "-".join(symbol) if isinstance(symbol, (list, tuple)) else symbol
    get = _http_get or _get_text
    url = QUOTE_URL.format(symbol=symbol)
    try:
        return get(url)
    except (RuntimeError, ValueError):
        pass
    sina = get(
        SINA_QUOTE_URL.format(symbol=tencent_symbol(symbol)), headers=_SINA_HEADERS
    )
    if '"' not in sina:
        raise RuntimeError("腾讯与新浪实时快照均不可用（请检查网络后重试）")
    return sina


def _get_text(url, headers=None):
    """拉取 URL 文本（GBK 解码），腾讯限流返回 none_match 时退避重试。

    headers：默认浏览器头（腾讯）；新浪需单独传 finance Referer。
    """
    for attempt in range(3):
        resp = None
        for session in (_direct_session, _default_session):
            try:
                resp = session.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                break
            except requests.RequestException:
                continue
        if resp is None:
            raise RuntimeError("实时快照请求失败（直连与代理均不可达）")
        body = resp.content.decode("gbk", errors="replace")
        if "none_match" not in body:
            return body
        time.sleep(2 * (attempt + 1))  # 限流退避：2s, 4s
    raise RuntimeError("腾讯实时快照被限流（多次返回 none_match），请稍后重试")


_SINA_HEADERS = {
    "User-Agent": _HEADERS["User-Agent"],
    "Referer": "https://finance.sina.com.cn",
}