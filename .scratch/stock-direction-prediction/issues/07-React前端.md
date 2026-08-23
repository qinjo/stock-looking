# 07 — 网页前端改用 React（Vite + TypeScript），双模式运行

**What to build:** 用户是前端，需要用自己的前端工具链维护页面。把原 Flask + 原生 JS 模板（`stocklook/templates/index.html`）换成 **React 18 + Vite 6 + TypeScript** 前端：

- `frontend/`：标准 Vite 工程。组件拆分 `App / SearchBar / StockCard / AnalysisBlock`，类型 `types.ts`、API 封装 `api.ts`，样式 `src/index.css`。
- **双模式**：
  - 生产：`cd frontend && npm run build` → 产物自动复制到 `stocklook/static/`，`python -m stocklook.webapp` 托管（SPA 路由回退 index.html）。
  - 开发：Flask 跑 8000 + `cd frontend && npm run dev`（5173，`/api` 代理到 Flask，HMR 热更新）。
- 后端 `POST /api/analyze` 接口不变，前端只对接它（向后兼容 CLI/notebook）。
- 未构建产物时 Flask 返回带标题的提示页（测试/首次访问不报错）；`stocklook/static` 与 `frontend/node_modules|dist` 均 gitignore。

**Blocked by:** 06（网页与 prompt 升级）——已解决。

**Status:** resolved

- [x] Vite + React + TS 工程骨架（npm 源 npmmirror，构建通过）
- [x] 组件化：SearchBar / StockCard / AnalysisBlock（多空证据、置信度条、风险、回测表、特征重要性）
- [x] dev 模式 HMR + `/api` proxy 验证通过（localhost:5173 → Flask 8000）
- [x] 生产模式 Flask 托管构建产物验证通过（/ 返回 React index.html，资源 200）
- [x] API 端到端正常（真 LLM：600519 down / 600036 flat）
- [x] pytest 46 全绿（webapp 测试适配静态 fallback，不依赖构建产物）

## Answer

（实现后填写）