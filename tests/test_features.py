import numpy as np
import pandas as pd
import pytest

from stocklook.features import FEATURE_COLS, add_features, build_label


def make_close_df(closes):
    n = len(closes)
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n, freq="B"),
            "open": closes,
            "close": closes,
            "high": closes,
            "low": closes,
            "volume": [1_000_000] * n,
            "amount": [1_000_000_000] * n,
            "amplitude": [0.02] * n,
            "pct_change": [0.0] * n,
            "change": [0.0] * n,
            "turnover": [1.0] * n,
        }
    )


class TestBuildLabel:
    def test_horizon_one_is_close_to_close(self):
        closes = [10.0, 10.5, 10.0, 11.0, 9.0, 10.2]
        df = make_close_df(closes)
        label = build_label(df, 1)
        expected = [1, 0, 1, 0, 1]
        assert label.iloc[:5].tolist() == expected

    def test_horizon_two_shifts_by_two(self):
        closes = [10.0, 10.0, 11.0, 9.0, 10.0, 10.5, 9.5]
        df = make_close_df(closes)
        label = build_label(df, 2)
        expected = [1, 0, 0, 1, 0]
        assert label.iloc[:5].tolist() == expected

    def test_tail_is_nan(self):
        closes = [10.0, 10.5, 11.0, 10.2, 9.5]
        df = make_close_df(closes)
        label = build_label(df, 1)
        assert label.iloc[-1] != label.iloc[-1]  # NaN
        assert int(label.iloc[-2]) == int(9.5 > 10.2)  # 0

    def test_threshold_keeps_default_binary_behavior(self):
        closes = [10.0, 10.5, 10.0, 11.0]
        df = make_close_df(closes)
        label = build_label(df, 1, threshold=0.0)
        assert label.iloc[:3].tolist() == [1.0, 0.0, 1.0]

    def test_threshold_neutralizes_tiny_moves(self):
        # 序列以约 1% / 0.1% 交替变动，阈值 0.5%
        closes = [100.0, 101.0, 101.101, 100.09, 99.99, 99.99]
        df = make_close_df(closes)
        label = build_label(df, 1, threshold=0.005)
        # i0: +1% → 涨；i1: +0.1% → 中性；i2: -1% → 跌；i3: -0.1% → 中性；i4: 0 → 中性；i5: NaN
        assert label.iloc[0] == 1.0
        assert label.iloc[1] != label.iloc[1]  # 微涨被中性化
        assert label.iloc[2] == 0.0
        assert label.iloc[3] != label.iloc[3]  # 微跌被中性化
        assert label.iloc[4] != label.iloc[4]  # 横盘被中性化
        assert label.iloc[5] != label.iloc[5]  # 尾行无未来数据


class TestAddFeatures:
    def test_feature_cols_are_present(self):
        closes = [10.0 + 0.1 * i for i in range(60)]
        df = make_close_df(closes)
        out = add_features(df)
        for col in FEATURE_COLS:
            assert col in out.columns

    def test_first_rows_have_nan_for_warmup(self):
        closes = [10.0 + 0.1 * i for i in range(60)]
        df = make_close_df(closes)
        out = add_features(df)
        assert out["ma20"].isna().iloc[:19].all()
        assert out["ma20"].notna().iloc[19]
