# stocklook — A股次日方向 · 参考信号

免费的数据 + 统计模型 + 大模型，对自选股下一个交易日的涨跌方向给出可解释的参考信号。

**流程**：实时/历史行情（腾讯接口，新浪兜底）→ 技术指标特征 → LightGBM walk-forward 回测 → DeepSeek 大模型分析（数据纪律 + 多空双视角）→ CLI / 网页展示。

> ⚠️ 仅供研究参考，不构成投资建议。个股短期方向接近随机，输出是概率信号，不是承诺。

## 安装

```bash
# Python 3.11+（macOS 上 LightGBM 需 brew install libomp）
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 前端（仅网页需要）
cd frontend && npm install && cd ..
```

## 配置（可选）

复制 `DEEPSEEK_API_KEY` 到 `.env`（已 gitignore）：

```bash
echo "DEEPSEEK_API_KEY=sk-xxxx" > .env
```

不配置也能用：只出 LightGBM 回测指标，跳过 LLM 分析。

## 网页（推荐）

```bash
./dev.sh          # 一键：Flask API(8000) + Vite 前端(5173, HMR)，自动开浏览器
```

或手动双起（开发模式）：
```bash
python -m stocklook.webapp      # 终端 1：后端 API http://127.0.0.1:8000
cd frontend && npm run dev      # 终端 2：前端 http://localhost:5173（/api 自动代理到后端）
```

生产构建（构建产物由后端托管）：
```bash
cd frontend && npm run build && cd ..
python -m stocklook.webapp      # http://127.0.0.1:8000
```

## CLI

```bash
python -m stocklook --stocks 600519 300750          # 回测指标 + 特征重要性
python -m stocklook --stocks 600519 --llm           # 追加 DeepSeek 分析
python -m stocklook --stocks 600519 --threshold 0.005  # 忽略 ±0.5% 内的微幅波动
```

## 测试

```bash
python -m pytest -q     # 46 个离线测试（不碰网络）
```

## 目录

- `stocklook/` — 数据（腾讯/新浪）· 特征 · 模型 · pipeline · LLM 分析 · webapp
- `frontend/` — React 18 + Vite + TypeScript 网页（`npm run dev` 开发 / `npm run build` 产物由后端托管）
- `notebooks/demo.ipynb` — 交互式探索
- `.scratch/stock-direction-prediction/` — spec 与问题记录（本地 markdown issue tracker）