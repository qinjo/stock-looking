"""轻量网页：输入股票代码 → 实时行情 + LLM 分析结果展示。

启动：`python -m stocklook.web`（默认 http://127.0.0.1:8000）
API：POST /api/analyze  body {"symbols": "600519,300750", "horizon": 1, "threshold": 0.0}
"""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from . import config
from .pipeline import analyze_symbol, llm_analysis

app = Flask(__name__, static_folder="static", static_url_path="/static")

_STATIC_DIR = Path(__file__).parent / "static"

# LLM 并发数：DeepSeek 请求是瓶颈；数据拉取有本地缓存
MAX_WORKERS = 3


@app.route("/")
def index():
    return _serve_frontend("index.html")


@app.errorhandler(404)
def _spa_fallback(_):
    """SPA 路由回退：静态产物存在时统一回到 index.html。"""
    return _serve_frontend("index.html")


def _serve_frontend(path):
    idx = _STATIC_DIR / "index.html"
    if idx.exists():
        return send_from_directory(_STATIC_DIR, path)
    return (
        "<html><body style='font-family:sans-serif;text-align:center;padding-top:80px'>"
        "<h1>📈 A股次日方向 · 参考信号</h1>"
        "<p>前端尚未构建：请先执行 <code>cd frontend && npm install && npm run build</code>，"
        "或开发模式运行 <code>cd frontend && npm run dev</code>（API 代理到本服务 8000 端口）。</p>"
        "</body></html>",
        200,
    )


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