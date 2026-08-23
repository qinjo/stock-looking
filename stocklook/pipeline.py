from datetime import datetime

import pandas as pd

from . import config
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
