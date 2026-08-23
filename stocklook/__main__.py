import argparse
from datetime import datetime

import pandas as pd

from . import config
from .data import fetch_history
from .features import FEATURE_COLS, add_features, build_label
from .model import evaluate, walk_forward_eval


def run(stocks, horizon):
    end_date = datetime.today().strftime("%Y%m%d")
    results = []
    for symbol in stocks:
        df = fetch_history(symbol, config.START_DATE, end_date, config.ADJUST)
        df = add_features(df)
        df["label"] = build_label(df, horizon)
        y_true, y_pred, y_prob = walk_forward_eval(
            df, FEATURE_COLS, "label", config.MIN_TRAIN_DAYS, config.WALK_STEP
        )
        metrics = evaluate(y_true, y_pred, y_prob)
        metrics["symbol"] = symbol
        results.append(metrics)
    return pd.DataFrame(results).set_index("symbol")


def main():
    parser = argparse.ArgumentParser(description="A股次日涨跌方向预测 demo")
    parser.add_argument(
        "--stocks", nargs="*", default=None, help="股票代码列表，默认用 config.DEFAULT_STOCKS"
    )
    parser.add_argument(
        "--horizon", type=int, default=None, help="预测未来第几个交易日，默认 config.HORIZON"
    )
    args = parser.parse_args()

    stocks = args.stocks or config.DEFAULT_STOCKS
    horizon = args.horizon if args.horizon is not None else config.HORIZON

    print(f"股票池: {stocks}  预测周期: T+{horizon}")
    summary = run(stocks, horizon)
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(summary)


if __name__ == "__main__":
    main()
