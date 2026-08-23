import argparse

import pandas as pd

from . import config
from .pipeline import run


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
    args = parser.parse_args()

    stocks = args.stocks or config.DEFAULT_STOCKS
    horizon = args.horizon if args.horizon is not None else config.HORIZON
    threshold = args.threshold if args.threshold is not None else config.THRESHOLD

    print(f"股票池: {stocks}  预测周期: T+{horizon}  阈值: {threshold}")
    summary, importances = run(stocks, horizon, threshold)
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(summary)

    print("\n=== 特征重要性（前 5） ===")
    for symbol, imp in importances.items():
        top = imp.head(5)
        text = ", ".join(f"{k}: {v:.4g}" for k, v in top.items())
        print(f"{symbol}: {text}")


if __name__ == "__main__":
    main()
