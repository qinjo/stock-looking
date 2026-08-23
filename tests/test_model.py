import numpy as np
import pandas as pd
import pytest

from stocklook.features import FEATURE_COLS, add_features, build_label
from stocklook.model import evaluate, feature_importances, walk_forward_eval


class TestEvaluate:
    def test_random_guessing_metrics_are_wellformed(self):
        rng = np.random.default_rng(7)
        y_true = rng.integers(0, 2, 400)
        y_pred = rng.integers(0, 2, 400)
        y_prob = rng.random(400)
        m = evaluate(y_true, y_pred, y_prob)
        assert 0 <= m["accuracy"] <= 1
        assert 0 <= m["auc"] <= 1
        assert m["n"] == 400
        assert m["tn"] + m["fp"] + m["fn"] + m["tp"] == 400

    def test_perfect_predictions_give_accuracy_one(self):
        y_true = np.array([0, 0, 1, 1, 1])
        y_pred = y_true.copy()
        y_prob = np.array([0.1, 0.2, 0.9, 0.8, 0.7])
        m = evaluate(y_true, y_pred, y_prob)
        assert m["accuracy"] == 1.0
        assert m["auc"] == 1.0
        assert m["tp"] == 3
        assert m["tn"] == 2
        assert m["win_rate"] == 1.0

    def test_single_class_auc_is_nan(self):
        y_true = np.array([1, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 1])
        y_prob = np.array([0.9, 0.9, 0.9, 0.9])
        m = evaluate(y_true, y_pred, y_prob)
        assert np.isnan(m["auc"])

    def test_win_rate_uses_true_labels(self):
        # 预测为涨的样本里，有多少真实为涨
        y_true = np.array([1, 1, 0, 1, 0, 0])
        y_pred = np.array([1, 1, 0, 1, 0, 0])
        y_prob = np.array([0.9, 0.8, 0.3, 0.7, 0.2, 0.4])
        m = evaluate(y_true, y_pred, y_prob)
        assert m["tp"] == 3
        assert m["fp"] == 0
        assert m["win_rate"] == 1.0
        assert m["up_rate"] == 3 / 6


class TestWalkForwardEval:
    def test_returns_aligned_predictions_on_synthetic(self, stock_df):
        df = add_features(stock_df)
        df["label"] = build_label(df, 1)
        y_true, y_pred, y_prob = walk_forward_eval(
            df, FEATURE_COLS, "label", min_train=500, step=60
        )
        assert len(y_true) == len(y_pred) == len(y_prob)
        assert len(y_true) > 0
        assert np.all((y_prob >= 0) & (y_prob <= 1))
        assert set(np.unique(y_pred)).issubset({0, 1})

    def test_matches_expected_test_row_count(self, stock_df):
        df = add_features(stock_df)
        df["label"] = build_label(df, 1)
        df = df.dropna(subset=FEATURE_COLS + ["label"]).reset_index(drop=True)
        n = len(df)
        expected = n - 500  # 从 500 开始直到末尾
        y_true, _, _ = walk_forward_eval(
            df, FEATURE_COLS, "label", min_train=500, step=60
        )
        assert len(y_true) == expected

    def test_raises_when_not_enough_data(self, stock_df):
        df = add_features(stock_df)
        df["label"] = build_label(df, 1)
        with pytest.raises(ValueError):
            walk_forward_eval(df, FEATURE_COLS, "label", min_train=2000, step=60)


class TestFeatureImportances:
    def test_returns_sorted_series(self, stock_df):
        df = add_features(stock_df)
        df["label"] = build_label(df, 1)
        imp = feature_importances(df, FEATURE_COLS, "label", n=5)
        assert len(imp) <= 5
        assert imp.index.isin(FEATURE_COLS).all()
        assert list(imp.values) == sorted(imp.values, reverse=True)
