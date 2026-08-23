from datetime import datetime

import pandas as pd

from . import config
from .analyst import (
    build_analysis_prompt,
    call_deepseek,
    fetch_quote,
    parse_llm_json,
    parse_quote,
)
from .data import fetch_history
from .features import FEATURE_COLS, add_features, build_label
from .model import evaluate, feature_importances, walk_forward_eval


def analyze_symbol(symbol, horizon, threshold=0.0, end_date=None):
    end_date = end_date or datetime.today().strftime("%Y%m%d")
    df = fetch_history(symbol, config.START_DATE, end_date, config.ADJUST)
    df = add_features(df)
    df["label"] = build_label(df, horizon, threshold)
    y_true, y_pred, y_prob = walk_forward_eval(
        df, FEATURE_COLS, "label", config.MIN_TRAIN_DAYS, config.WALK_STEP
    )
    metrics = evaluate(y_true, y_pred, y_prob)
    metrics["symbol"] = symbol
    importances = feature_importances(df, FEATURE_COLS, "label")
    return df, metrics, importances


def run(stocks, horizon, threshold=0.0):
    results = []
    importances = {}
    for symbol in stocks:
        _, metrics, imp = analyze_symbol(symbol, horizon, threshold)
        results.append(metrics)
        importances[symbol] = imp
    return pd.DataFrame(results).set_index("symbol"), importances


def llm_analysis(symbol, api_key, horizon=1, threshold=0.0, _http_post=None,
                 df=None, metrics=None, importances=None):
    """单只股票的 LLM 分析：可复用已有历史管线结果，叠加实时快照后调 DeepSeek。

    返回 dict：{symbol, quote, analysis(解析后 JSON), raw(原始回复)}。
    df/metrics/importances 未传入时内部调用 analyze_symbol 计算（CLI 场景）。
    """
    if df is None or metrics is None or importances is None:
        df, metrics, importances = analyze_symbol(symbol, horizon, threshold)
    quote = parse_quote(fetch_quote(symbol), code=symbol)
    system, prompt = build_analysis_prompt(
        symbol, quote, df, metrics=metrics, importances=importances
    )
    raw = call_deepseek(prompt, api_key, system=system, _http_post=_http_post)
    try:
        analysis = parse_llm_json(raw)
    except ValueError:
        analysis = None
    return {"symbol": symbol, "quote": quote, "analysis": analysis, "raw": raw}


def llm_analyses(stocks, api_key, horizon=1, threshold=0.0, _http_post=None):
    """批量：对股票池逐只做 LLM 分析，返回 {symbol: result}。"""
    return {
        symbol: llm_analysis(symbol, api_key, horizon, threshold, _http_post)
        for symbol in stocks
    }
