import pandas as pd
import pytest
import requests

from stocklook import config
from stocklook.data import (
    fetch_history,
    merge_pages,
    parse_tencent_kline,
    tencent_symbol,
)

_PAGE = 640


def _tx_payload(symbol, rows, key="qfqday"):
    return {"code": 0, "msg": "", "data": {symbol: {key: rows}}}


def _kline_row(day, price):
    return [day, f"{price:.3f}", f"{price + 0.5:.3f}", f"{price + 2:.3f}", f"{price - 1:.3f}", "10000.000"]


class TestTencentSymbol:
    def test_shanghai_prefix(self):
        assert tencent_symbol("600519") == "sh600519"
        assert tencent_symbol("601318") == "sh601318"
        assert tencent_symbol("688981") == "sh688981"

    def test_shenzhen_prefix(self):
        assert tencent_symbol("000001") == "sz000001"
        assert tencent_symbol("300750") == "sz300750"
        assert tencent_symbol("002415") == "sz002415"

    def test_beijing_prefix(self):
        assert tencent_symbol("830799") == "bj830799"

    def test_unknown_prefix_raises(self):
        with pytest.raises(ValueError):
            tencent_symbol("ABC123")


class TestParseTencentKline:
    def test_parses_qfqday_into_canonical_columns(self):
        payload = _tx_payload(
            "sh600519",
            [
                _kline_row("2025-06-03", 1428.429),
                _kline_row("2025-06-02", 1400.0),
            ],
        )
        df = parse_tencent_kline(payload)
        assert list(df.columns) == ["date", "open", "close", "high", "low", "volume"]
        assert len(df) == 2
        assert df["date"].is_monotonic_increasing
        assert df["close"].iloc[-1] == pytest.approx(1428.929)

    def test_falls_back_to_unadjusted_day_key(self):
        payload = _tx_payload("sh600519", [_kline_row("2025-06-03", 100.0)], key="day")
        df = parse_tencent_kline(payload)
        assert len(df) == 1

    def test_empty_payload_raises(self):
        with pytest.raises(ValueError):
            parse_tencent_kline({})

    def test_dividend_rows_with_extra_field_are_truncated(self):
        # 除息日行带第 7 个分红 dict 字段，解析时只取前 6 列
        rows = [
            _kline_row("2025-06-26", 1363.019),
            [
                "2025-06-25", "1367.000", "1365.000", "1370.000", "1355.000", "34000.000",
                {"nd": "2024", "fh_sh": "276.73", "djr": "2025-06-24", "cqr": "2025-06-25"},
            ],
        ]
        payload = _tx_payload("sh600519", rows)
        df = parse_tencent_kline(payload)
        assert len(df) == 2
        assert list(df.columns) == ["date", "open", "close", "high", "low", "volume"]
        assert "nd" not in df.columns


class TestMergePages:
    def test_deduplicates_and_sorts(self):
        p1 = pd.DataFrame(
            {"date": pd.to_datetime(["2025-06-01", "2025-06-02"]),
             "close": [1.0, 2.0]}
        )
        p2 = pd.DataFrame(
            {"date": pd.to_datetime(["2025-06-02", "2025-06-03"]),
             "close": [99.0, 3.0]}  # 06-02 重叠，保留先出现的 2.0
        )
        merged = merge_pages([p1, p2])
        assert list(merged["date"]) == list(pd.to_datetime(["2025-06-01", "2025-06-02", "2025-06-03"]))
        assert merged["close"].iloc[1] == 2.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            merge_pages([])


class TestFetchHistoryOffline:
    def test_paginates_and_writes_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
        # 完整序列 643 个交易日，腾讯语义：每次返回 [beg, end] 内最近 _PAGE 条
        all_days = pd.date_range("2025-01-01", periods=_PAGE + 3, freq="B")

        def fake_get(symbol, adjust, beg, end):
            calls.append((symbol, adjust, beg, end))
            beg_dt = pd.Timestamp(beg)
            end_dt = pd.Timestamp(end)
            rows = [
                _kline_row(d.strftime("%Y-%m-%d"), 10.0 + i * 0.01)
                for i, d in enumerate(all_days)
                if beg_dt <= d <= end_dt
            ]
            return _tx_payload("sh600519", rows[-_PAGE:])

        calls = []
        df = fetch_history("600519", "20250101", "20281231", _http_get=fake_get)
        assert len(df) == _PAGE + 3
        assert df["date"].is_monotonic_increasing
        assert len(calls) == 2
        assert calls[0][0] == "sh600519"
        assert calls[0][1] == "qfq"
        # 第二页向前翻：end 推到第一页首条日期之前一天
        assert calls[1][3] < calls[0][3]
        # 缓存写入：第二次调用直接读缓存，不再请求
        cached = fetch_history("600519", "20250101", "20281231", _http_get=fake_get)  # noqa: F821
        assert len(cached) == _PAGE + 3
        assert len(calls) == 2

    def test_network_error_raises_runtime_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))

        def failing_get(symbol, adjust, beg, end):
            raise requests.ConnectionError("boom")

        with pytest.raises(RuntimeError):
            fetch_history("600519", "20250101", "20261231", _http_get=failing_get)