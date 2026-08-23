import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def stock_df():
    rng = np.random.default_rng(123)
    n = 1200
    ret = rng.normal(0.0004, 0.02, n)
    close = 100 * np.exp(np.cumsum(ret))
    return pd.DataFrame(
        {
            "date": pd.date_range("2015-01-01", periods=n, freq="B"),
            "open": close * (1 + rng.normal(0, 0.003, n)),
            "close": close,
            "high": close * (1 + np.abs(rng.normal(0, 0.005, n))),
            "low": close * (1 - np.abs(rng.normal(0, 0.005, n))),
            "volume": rng.integers(1_000_000, 5_000_000, n),
            "amount": rng.integers(1_000_000_000, 5_000_000_000, n),
            "amplitude": np.abs(rng.normal(0.03, 0.01, n)),
            "pct_change": ret * 100,
            "change": close * ret,
            "turnover": np.abs(rng.normal(2.0, 0.5, n)),
        }
    )
