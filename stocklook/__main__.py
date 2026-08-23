import argparse
import os

import pandas as pd

from . import config
from .pipeline import llm_analyses, run


def _fmt(v, nd=2):
    return f"{v:.{nd}f}" if v is not None else "--"


def _print_analysis(result):
    symbol = result["symbol"]
    quote = result["quote"]
    name = quote.get("name") or symbol
    ts = quote.get("time")
    t_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "未知"
    print(f"\n=== {symbol} {name}  LLM 分析（快照时间 {t_str}） ===")
    print(
        f"现价 {_fmt(quote.get('price'))}  涨跌 {_fmt(quote.get('change'))} "
        f"({_fmt(quote.get('change_pct'))}%)  换手 {_fmt(quote.get('turnover'))}%  "
        f"量比 {_fmt(quote.get('volume_ratio'))}"
    )
    analysis = result["analysis"]
    if analysis is None:
        print("（模型未返回可解析的 JSON，原文如下）")
        print(result["raw"])
        return
    direction = {
        "up": "看涨",
        "down": "看跌",
        "flat": "横盘/方向不明",
    }.get(analysis.get("direction"), analysis.get("direction"))
    conf = analysis.get("confidence")
    print(f"方向: {direction}  置信度: {conf if conf is not None else '未知'}")
    if analysis.get("bull_cases") or analysis.get("bear_cases"):
        print("看涨证据:")
        for c in analysis.get("bull_cases", []):
            print(f"  ▲ {c}")
        print("看跌证据:")
        for c in analysis.get("bear_cases", []):
            print(f"  ▼ {c}")
    for reason in analysis.get("reasons", []):
        print(f"  - {reason}")
    if analysis.get("risks"):
        print("风险:")
        for risk in analysis["risks"]:
            print(f"  ! {risk}")
    if analysis.get("summary"):
        print(f"总结: {analysis['summary']}")


def main():
    parser = argparse.ArgumentParser(description="A股次日涨跌方向预测 demo")
    parser.add_argument(
        "--stocks", nargs="*", default=None, help="股票代码列表，默认用 config.DEFAULT_STOCKS"
    )
    parser.add_argument(
        "--horizon", type=int, default=None, help="预测未来第几个交易日，默认 config.HORIZON"
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="忽略接近零的涨跌幅阈值（默认 config.THRESHOLD，即不做中性过滤）",
    )
    parser.add_argument(
        "--llm", action="store_true", help="追加 DeepSeek 大模型分析（需 API key）"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="DeepSeek API key；不传则读环境变量 DEEPSEEK_API_KEY（推荐，避免 key 入 git）",
    )
    args = parser.parse_args()

    stocks = args.stocks or config.DEFAULT_STOCKS
    horizon = args.horizon if args.horizon is not None else config.HORIZON
    threshold = args.threshold if args.threshold is not None else config.THRESHOLD
    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")

    print(f"股票池: {stocks}  预测周期: T+{horizon}  阈值: {threshold}")
    summary, importances = run(stocks, horizon, threshold)
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(summary)

    print("\n=== 特征重要性（前 5） ===")
    for symbol, imp in importances.items():
        top = imp.head(5)
        text = ", ".join(f"{k}: {v:.4g}" for k, v in top.items())
        print(f"{symbol}: {text}")

    if args.llm:
        if not api_key:
            print("\n[跳过 LLM] 未提供 API key：请设置环境变量 DEEPSEEK_API_KEY 或传 --api-key")
        else:
            analyses = llm_analyses(stocks, api_key, horizon, threshold)
            for result in analyses.values():
                _print_analysis(result)


if __name__ == "__main__":
    main()