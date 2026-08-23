# 05 — 实时行情 + DeepSeek LLM 分析（这才是最初想要的功能）

**What to build:** 实现最初设想的核心功能：**实时抓取指定股票的行情快照与近期走势，打包成 prompt 发给 DeepSeek 大模型分析**，输出「明日涨/跌/横盘判断 + 置信度 + 关键理由」，作为投资参考信号。

- 实时快照：腾讯 `qt.gtimg.cn/q=sh600519`（已实测直连可用，GBK 编码，`~` 分隔字段）。
- 新模块 `stocklook/analyst.py`：
  - `parse_tencent_quote(text)`：纯函数解析快照文本 → 规整字段 dict（现价/昨收/今开/最高/最低/涨跌/涨跌幅/成交量/成交额/换手率/振幅/时间 等），离线可测。
  - `build_analysis_prompt(snapshot, recent_df, metrics, importances)`：纯函数把快照 + 近 N 日走势 + 技术指标摘要 + 回测结果拼成结构化 prompt，明确要求模型输出 JSON（direction / confidence / reasons / risks）。
  - `analyze(symbol, api_key, ...)`：协调 拉快照 → 拉近期历史 → 拼 prompt → 调 DeepSeek → 解析输出。
- DeepSeek 接入：`https://api.deepseek.com/chat/completions`，model `deepseek-chat`，OpenAI 兼容格式。
- **API key 安全**：只从环境变量 `DEEPSEEK_API_KEY` 或 CLI `--api-key` 读，**绝不写入代码、配置文件或 git**；设计上不允许把 key 序列化进结果。
- 调用 seam：`call_deepseek` 接受注入的 `_http_post` 便于离线测试；prompt/输出解析均为纯函数。
- CLI：新增 `--llm` 开关，`python -m stocklook --stocks 600519 --llm` 输出大模型分析。
- 预期管理：LLM 判断同样不承诺准确性，输出置于「参考信号」框架内（沿用 spec 的定位）。

**Blocked by:** 04（数据源换成腾讯接口）——已解决。

**Status:** resolved

- [x] 确认腾讯实时快照字段结构（curl 实测并核对每个字段含义）
- [x] 确认 DeepSeek API 可达性（直连 or 代理），鉴权与模型名正确
- [x] `parse_tencent_quote` 纯函数 + 离线测试
- [x] `build_analysis_prompt` 纯函数 + 离线测试
- [x] `analyze` 端到端（注入式调用 + 真机验证一次）
- [x] CLI `--llm` 开关
- [x] API key 只走环境变量，不进 git

## Answer

已实现，默认股票池 5 只全部端到端跑通。`stocklook/analyst.py`：

- **实时快照**：腾讯 `qt.gtimg.cn/q=sh600519`（88 字段，含振幅/换手/量比）；实测腾讯对短时高频请求返回 `v_pv_none_match="1"` 限流（窗口 >60s），故实现**腾讯优先 + 新浪 `hq.sinajs.cn` 兜底**双源自动切换（新浪 34 字段版缺换手/振幅/量比，由现价昨收推算涨跌幅，字段置 None 并在 prompt/CLI 显示 `--`）。两个源都限流时退避重试后报清晰错误。
- **DeepSeek**：`api.deepseek.com/chat/completions`，`deepseek-chat`（实测映射为 `deepseek-v4-flash`），直连优先 + 代理兜底，温度 0.3。
- **纯函数 seam**：`parse_tencent_quote` / `parse_sina_quote` / `parse_quote`（按分隔符自动分派）、`build_analysis_prompt`（快照 + 近 30 日走势 + 今日技术指标 + walk-forward 回测参考 + 驱动特征，要求输出严格 JSON）、`parse_llm_json`（容错 ```json 代码块与前后杂文）。
- **网络 seam**：`fetch_quote(_http_get)` / `call_deepseek(_http_post)` 注入式，离线测试不碰网络。
- **pipeline**：`llm_analysis` / `llm_analyses` 复用 `analyze_symbol` 的 df/metrics/importances，不重复计算；解析失败时保留模型原文供查看。
- **CLI**：`--llm` 开关；API key 仅从环境变量 `DEEPSEEK_API_KEY` 或 `--api-key` 读取，代码/配置/提交均不含 key（已 grep 核查）。无 key 时明确提示跳过。
- **Q&A（真实调用）**：600519 看跌 0.55（破 MA5/20 空头排列、MACD 负柱、量能不足）；300750 看涨 0.55（超跌反弹、量能恢复、上方均线压力）；600036 横盘（均线交织、量能萎缩、多空矛盾）；601318 看涨 0.55（放量突破短期均线、量比 1.60）。全部给出理由/风险/总结，置信度均标注回测接近随机的不确定性。
- 测试 42 个全绿（新增 15 个 LLM 相关）。