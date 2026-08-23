import os

import pandas as pd
import pytest

from stocklook import webapp
from stocklook.analyst import parse_tencent_quote


@pytest.fixture
def fake_symbol(monkeypatch):
    """离线化：替换数据/模型管线，不碰网络。"""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-07-01", periods=40, freq="B"),
            "close": [100.0] * 40,
            "volume": [1_000_000] * 40,
            "ret": [0.0] * 40,
        }
    )

    def fake_analyze_symbol(symbol, horizon, threshold):
        metrics = {"n": 2308, "up_rate": 0.5, "accuracy": 0.5, "auc": 0.5,
                   "win_rate": 0.5, "tn": 1, "fp": 1, "fn": 1, "tp": 1}
        imp = pd.Series({"ret_lag1": 300, "macd": 200})
        return df, metrics, imp

    monkeypatch.setattr(webapp, "analyze_symbol", fake_analyze_symbol)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return df


@pytest.fixture
def client(fake_symbol):
    webapp.app.config["TESTING"] = True
    return webapp.app.test_client()


class TestWebApp:
    def test_index_serves_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "A股次日方向" in resp.get_data(as_text=True)

    def test_analyze_requires_symbols(self, client):
        resp = client.post("/api/analyze", json={"symbols": "  , ，   "})
        assert resp.status_code == 400

    def test_analyze_returns_metrics_without_llm(self, client):
        resp = client.post("/api/analyze", json={"symbols": "600519,300750"})
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["llm_enabled"] is False
        results = body["results"]
        assert len(results) == 2
        assert [r["symbol"] for r in results] == ["600519", "300750"]
        assert results[0]["metrics"]["n"] == 2308
        assert results[0]["importances"]["ret_lag1"] == 300
        assert "未设置" in results[0]["error"]

    def test_single_failure_does_not_break_batch(self, fake_symbol, client, monkeypatch):
        def broken(symbol, horizon, threshold):
            if symbol == "600519":
                raise RuntimeError("boom")
            metrics = {"n": 10, "up_rate": 0.5, "accuracy": 0.6, "auc": 0.6,
                       "win_rate": 0.6, "tn": 2, "fp": 2, "fn": 2, "tp": 2}
            return fake_symbol, metrics, pd.Series({"ret": 1})

        monkeypatch.setattr(webapp, "analyze_symbol", broken)
        resp = client.post("/api/analyze", json={"symbols": "600519,000001"})
        body = resp.get_json()
        assert body["results"][0]["error"].startswith("RuntimeError")
        assert body["results"][1]["metrics"] is not None