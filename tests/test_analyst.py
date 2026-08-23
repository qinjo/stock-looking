import pandas as pd
import pytest

from stocklook.analyst import (
    build_analysis_prompt,
    call_deepseek,
    fetch_quote,
    parse_llm_json,
    parse_quote,
    parse_sina_quote,
    parse_tencent_quote,
)

# 从真实接口抓取的 600519 快照（GBK 解码后，88 字段）
REAL_QUOTE = (
    'v_sh600519="1~贵州茅台~600519~1272.83~1291.50~1291.50~33472~13331~20142'
    "~1272.83~1~1272.81~2~1272.80~12~1272.78~1~1272.77~1~1272.90~1~1272.96~2"
    "~1272.97~19~1272.98~6~1272.99~1~~20260821161449~-18.67~-1.45~1291.50"
    "~1272.01~1272.83/33472/4278311022~33472~427831~0.27~19.54~~1291.50"
    '~1272.01~1.51~15911.41~15911.41~6.33~1420.65~1162.35~0.80";'
)


class TestParseTencentQuote:
    def test_parses_real_fields(self):
        q = parse_tencent_quote(REAL_QUOTE)
        assert q["name"] == "贵州茅台"
        assert q["code"] == "600519"
        assert q["price"] == 1272.83
        assert q["prev_close"] == 1291.50
        assert q["change"] == -18.67
        assert q["change_pct"] == -1.45
        assert q["turnover"] == 0.27
        assert q["amplitude"] == 1.51
        assert q["volume_ratio"] == 0.80
        assert q["amount_wan"] == 427831
        assert q["time"].strftime("%Y-%m-%d %H:%M") == "2026-08-21 16:14"

    def test_multiple_symbols_parses_first(self):
        text = REAL_QUOTE + '\nv_sh600036="1~招商银行~600036~35.00~34.50~34.60~1~2~3";\n'
        q = parse_tencent_quote(text)
        assert q["code"] == "600519"

    def test_empty_fields_become_none(self):
        # 满 50 个字段，但价格/昨收/时间等关键字段留空
        fields = [str(i) for i in range(50)]
        fields[1] = "某股"
        fields[2] = "600000"
        for idx in (3, 4, 30):
            fields[idx] = ""
        text = f'v_sh600000="{"~" .join(fields)}";'
        q = parse_tencent_quote(text)
        assert q["price"] is None
        assert q["prev_close"] is None
        assert q["time"] is None

    def test_malformed_raises(self):
        with pytest.raises(ValueError):
            parse_tencent_quote("no quotes here")


SINA_QUOTE = (
    'var hq_str_sh600519="贵州茅台,1291.500,1291.500,1272.830,1291.500,1272.010,'
    "1272.830,1272.900,3347231,4278311022.000,122,1272.830,200,1272.810,1200,1272.800,"
    "100,1272.780,100,1272.770,100,1272.900,200,1272.960,1900,1272.970,611,1272.980,"
    '100,1272.990,2026-08-21,15:34:58,00,D|1300|1654679.00";'
)


class TestParseSinaQuote:
    def test_parses_and_derives_change(self):
        q = parse_sina_quote(SINA_QUOTE, code="600519")
        assert q["name"] == "贵州茅台"
        assert q["code"] == "600519"
        assert q["price"] == pytest.approx(1272.83)
        assert q["prev_close"] == pytest.approx(1291.50)
        assert q["change"] == pytest.approx(-18.67, abs=1e-2)
        assert q["change_pct"] == pytest.approx(-1.446, abs=1e-2)
        assert q["volume"] == pytest.approx(33472.31)  # 股 -> 手
        assert q["amount_wan"] == pytest.approx(427831.1022)
        assert q["time"].strftime("%Y-%m-%d %H:%M") == "2026-08-21 15:34"
        assert q["turnover"] is None  # 新浪缺换手/振幅/量比


class TestParseQuoteDispatch:
    def test_dispatch_tencent_by_tilde(self):
        q = parse_quote(REAL_QUOTE)
        assert q["turnover"] == 0.27

    def test_dispatch_sina_by_comma(self):
        q = parse_quote(SINA_QUOTE, code="600519")
        assert q["name"] == "贵州茅台"
        assert q["change_pct"] == pytest.approx(-1.446, abs=1e-2)


class TestParseLlmJson:
    def test_plain_json(self):
        out = parse_llm_json('{"direction": "up", "confidence": 0.6}')
        assert out["direction"] == "up"

    def test_code_fence_json(self):
        out = parse_llm_json('```json\n{"direction": "down", "confidence": 0.7}\n```')
        assert out["direction"] == "down"

    def test_surrounding_text_is_ignored(self):
        out = parse_llm_json(
            '好的，这是我的判断：{"direction": "flat", "confidence": 0.5, "reasons": ["a"]} 仅供参考。'
        )
        assert out["direction"] == "flat"

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            parse_llm_json("我没有 JSON 可给")


class TestBuildAnalysisPrompt:
    def _df(self):
        n = 40
        closes = [100.0 + i * 0.1 for i in range(n)]
        df = pd.DataFrame(
            {
                "date": pd.date_range("2026-07-01", periods=n, freq="B"),
                "close": closes,
                "volume": [1_000_000] * n,
                "pct_change": [0.1] * n,
                "ret": [0.001] * n,
                "ma5": [110.0] * n,
                "ma10": [108.0] * n,
                "ma20": [105.0] * n,
                "close_over_ma5": [0.01] * n,
                "close_over_ma20": [0.02] * n,
                "rsi14": [55.0] * n,
                "macd": [0.5] * n,
                "macd_signal": [0.4] * n,
                "macd_hist": [0.1] * n,
                "volume_ratio": [1.2] * n,
                "position20": [0.7] * n,
            }
        )
        return df

    def test_prompt_contains_markets_snapshot_and_task(self):
        q = parse_tencent_quote(REAL_QUOTE)
        system, user = build_analysis_prompt("600519", q, self._df())
        assert "贵州茅台" in user
        assert "1272.83" in user
        assert "direction" in user
        assert '"up|down|flat"' in user
        assert "RSI14 55.0" in user
        assert "参考信号而非承诺" in system

    def test_prompt_include_metrics_when_given(self):
        q = parse_tencent_quote(REAL_QUOTE)
        metrics = {"n": 100, "up_rate": 0.5, "accuracy": 0.5, "auc": 0.5, "win_rate": 0.5}
        _, user = build_analysis_prompt("600519", q, self._df(), metrics=metrics)
        assert "walk-forward" in user
        assert "0.50" in user


class TestCallDeepseek:
    def test_returns_content_from_injected_post(self):
        def fake_post(url, payload, headers):
            assert url.endswith("/chat/completions")
            assert headers["Authorization"].startswith("Bearer ")
            assert payload["messages"][-1]["content"] == "hi"
            return {"choices": [{"message": {"content": '{"direction":"up"}'}}]}

        out = call_deepseek("hi", "sk-test", _http_post=fake_post)
        assert out == '{"direction":"up"}'

    def test_http_error_raises_runtime_error(self):
        def fake_post(url, payload, headers):
            raise RuntimeError("DeepSeek API 错误 401: bad key")

        with pytest.raises(RuntimeError):
            call_deepseek("hi", "sk-test", _http_post=fake_post)