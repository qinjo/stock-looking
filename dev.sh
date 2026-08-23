#!/usr/bin/env bash
# 一键启动开发环境：Flask 后端(8000) + Vite 前端(5173, HMR)
# 用法：./dev.sh   （Ctrl+C 一起退出，浏览器自动打开 http://localhost:5173）
set -e
cd "$(dirname "$0")"

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "未找到虚拟环境 .venv"
  echo "请先执行：python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
  exit 1
fi

_cleaned=0
cleanup() {
  [ "$_cleaned" = 1 ] && return
  _cleaned=1
  echo
  echo "正在关闭后端与前端…"
  jobs -p | xargs -r kill 2>/dev/null || true
  sleep 1
  jobs -p | xargs -r kill -9 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM EXIT

# 端口占用检查
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[警告] 8000 端口已被占用，跳过启动 Flask（如已是本项目后端可忽略）"
else
  echo "[1/2] 启动 Flask API → http://127.0.0.1:8000"
  "$PY" -m stocklook.webapp &
  sleep 2
fi

cd frontend
if [ ! -d node_modules ]; then
  echo "首次运行，安装前端依赖…"
  npm install
fi

if lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[警告] 5173 端口已被占用，跳过后端启动。"
  echo "      请确认是 vite dev server；否则先关掉占用进程再运行本脚本。"
else
  echo "[2/2] 启动 Vite 前端 → http://localhost:5173 (Ctrl+C 退出)"
  npm run dev &
  sleep 4
  (open http://localhost:5173 >/dev/null 2>&1 || true)
fi

wait