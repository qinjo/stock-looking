"""轻量网页：输入股票代码 → 实时行情 + LLM 分析结果展示。

启动：`python -m stocklook.web`（默认 http://127.0.0.1:8000）
API：POST /api/analyze  body {"symbols": "600519,300750", "horizon": 1, "threshold": 0.0}
"""
import os
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, render_template, request

from . import config
from .pipeline import analyze_symbol, llm_analysis

app = Flask(__name__)

# LLM 并发数：DeepSeek 请求是瓶颈；数据拉取有本地缓存
MAX_WORKERS = 3


@app.route("/")
def index():
    return render_template("index.html")


def _quote_to_json(quote):
    """quote dict 中的 datetime 转 ISO 字符串，便于 JSON 传输与前端 new Date() 解析。"""
    q = dict(quote or {})
    t = q.get("time")
    if t is not None:
        q["time"] = t.isoformat()
    return q


def _analyze_one(symbol, horizon, threshold, api_key):
    try:
        df, metrics, importances = analyze_symbol(symbol, horizon, threshold)
        result = {
            "symbol": symbol,
            "metrics": metrics,
            "importances": importances.head(8).to_dict(),
            "quote": None,
            "analysis": None,
            "raw": None,
            "error": None,
        }
        if api_key:
            llm = llm_analysis(
                symbol, api_key, horizon, threshold,
                df=df, metrics=metrics, importances=importances,
            )
            result["quote"] = _quote_to_json(llm["quote"])
            result["analysis"] = llm["analysis"]
            result["raw"] = llm["raw"]
        else:
            result["error"] = "未设置 DEEPSEEK_API_KEY，跳过 LLM 分析（仅回测指标）"
        return result
    except Exception as exc:  # 单只失败不拖垮整批
        return {"symbol": symbol, "error": f"{type(exc).__name__}: {exc}",
                "metrics": None, "importances": None, "quote": None,
                "analysis": None, "raw": None}


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(force=True) or {}
    raw = data.get("symbols") or ""
    symbols = [s.strip() for s in raw.replace("，", ",").split(",") if s.strip()]
    if not symbols:
        return jsonify({"error": "请输入股票代码，如 600519"}), 400
    try:
        horizon = int(data.get("horizon") or config.HORIZON)
        threshold = float(data.get("threshold") or config.THRESHOLD)
    except ValueError:
        return jsonify({"error": "horizon/threshold 必须为数字"}), 400
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(symbols))) as pool:
        results = list(pool.map(
            lambda s: _analyze_one(s, horizon, threshold, api_key), symbols
        ))
    return jsonify({"results": results, "llm_enabled": bool(api_key)})


def main():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("[警告] 未设置 DEEPSEEK_API_KEY（.env 可配置），LLM 分析将跳过")
    print("股票分析页: http://127.0.0.1:8000  (Ctrl+C 退出)")
    app.run(host="127.0.0.1", port=8000, debug=False)


if __name__ == "__main__":
    main()