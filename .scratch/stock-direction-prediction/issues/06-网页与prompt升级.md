# 06 — .env 密钥管理 + 网页端展示 + LLM prompt 参考 TradingAgents

**What to build:** 三个诉求：

1. **Key 管理**：API key 存 `.env`（gitignore），CLI 与网页自动读取，不再依赖手动 export。
2. **网页端**：`python -m stocklook.webapp` 启动本地页面（http://127.0.0.1:8000），输入股票代码 → 实时快照 + LightGBM 回测 + DeepSeek 分析，结果卡片式展示（方向徽章/多空证据/置信度/风险/回测表/特征重要性）。
3. **Prompt 升级**：参考 TradingAgents 的 prompt 设计——数据纪律（给定快照与指标是唯一事实来源，精确 OHLCV/价格/百分比必须有数据支持，冲突指出来而非编造调和值）、指标解读提示（RSI 70/30、MACD 金叉死叉/柱状动能、量价配合）、多空双视角（先列看涨/看跌证据再综合）——JSON 输出新增 `bull_cases` / `bear_cases`。

**Blocked by:** 05（实时行情 + LLM 分析）——已解决。

**Status:** resolved

- [x] `.env` 由 `config._load_env()`（python-dotenv）自动加载，不覆盖已存在的环境变量
- [x] `.env` 加入 .gitignore，key 不进 git（已核查）
- [x] `stocklook/webapp.py`：Flask 单文件，GET `/` 页面 + POST `/api/analyze`
- [x] `stocklook/templates/index.html`：输入框 + 卡片渲染（原生 JS，无外部依赖）
- [x] `llm_analysis` 支持注入 df/metrics/importances，网页端不重复计算；多股票 ThreadPoolExecutor 并发（max 3）
- [x] TradingAgents 风格 prompt：数据纪律 / 指标解读 / 多空双视角；CLI 同步渲染 bull/bear
- [x] 端到端验证：网页 API 3 只并发全通（down/flat/up），模型给出的证据均带具体日期与价格

## Answer

（实现后填写）