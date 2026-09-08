#!/usr/bin/env bash
#
# AI Agent 平台 — 启停/管理脚本(根目录入口)
#
# 用法:
#   ./dev.sh start                启动 backend + frontend
#   ./dev.sh stop                 停止 backend + frontend
#   ./dev.sh restart              重启 backend + frontend
#   ./dev.sh status               查看运行状态
#   ./dev.sh logs                 查看日志尾部(backend + frontend)
#   ./dev.sh logs -f              实时跟随日志
#   ./dev.sh logs backend         只看 backend 日志
#   ./dev.sh logs frontend        只看 frontend 日志
#   ./dev.sh backend              只启动 backend
#   ./dev.sh frontend             只启动 frontend
#   ./dev.sh build                构建前端生产包
#   ./dev.sh health               健康检查(HTTP)
#   ./dev.sh clean                停止服务并清理日志/pid/构建产物
#   ./dev.sh help                 显示本帮助
#
# 可选参数(需放在子命令之后):
#   --port <N>       backend 端口(默认 8000)
#   --host <H>       backend 监听地址(默认 127.0.0.1)
#   --ui-port <N>    frontend 端口(默认 5173)
#   --ui-host <H>    frontend 监听地址(默认 127.0.0.1)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

# Prefer the repository virtual environment when it exists, keeping runtime
# dependencies isolated from the system Python installation.
BACKEND_PYTHON="python3"
if [ -x "$ROOT/backend/.venv/bin/python" ] \
  && "$ROOT/backend/.venv/bin/python" -c 'import fastapi, uvicorn, langgraph, openviking' >/dev/null 2>&1; then
  BACKEND_PYTHON="$ROOT/backend/.venv/bin/python"
fi

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
UI_HOST="127.0.0.1"
UI_PORT="5173"
FOLLOW=""

BACKEND_PID="$RUN_DIR/backend.pid"
FRONTEND_PID="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
LOG_TARGET="all"

usage() {
  sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

is_running() {
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts=0
  while [ "$attempts" -lt 30 ]; do
    if curl --noproxy '*' -fsS -o /dev/null "$url" 2>/dev/null; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.5
  done
  echo "$label 启动失败，请查看对应日志"
  return 1
}

start_backend() {
  if is_running "$BACKEND_PID"; then
    echo "backend 已在运行 (pid $(cat "$BACKEND_PID"))"
    return
  fi
  if ! "$BACKEND_PYTHON" -c 'import fastapi, uvicorn, langgraph, openviking' >/dev/null 2>&1; then
    echo "backend 依赖未安装。请执行: $BACKEND_PYTHON -m pip install -r $ROOT/backend/requirements.txt"
    return 1
  fi
  echo "启动 backend  -> http://$BACKEND_HOST:$BACKEND_PORT"
  (
    cd "$ROOT/backend"
    setsid "$BACKEND_PYTHON" -m uvicorn app.main:app \
      --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
      >> "$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! > "$BACKEND_PID"
  )
  if ! is_running "$BACKEND_PID"; then
    echo "backend 进程未能启动，请查看 $BACKEND_LOG"
    rm -f "$BACKEND_PID"
    return 1
  fi
  wait_for_url "http://$BACKEND_HOST:$BACKEND_PORT/health" "backend"
  echo "backend 已启动 (pid $(cat "$BACKEND_PID"))"
}

start_frontend() {
  if is_running "$FRONTEND_PID"; then
    echo "frontend 已在运行 (pid $(cat "$FRONTEND_PID"))"
    return
  fi
  echo "启动 frontend -> http://$UI_HOST:$UI_PORT"
  (
    cd "$ROOT/frontend/react-app"
    VITE_BACKEND_PORT="$BACKEND_PORT" setsid npm run dev -- --host "$UI_HOST" --port "$UI_PORT" \
      >> "$FRONTEND_LOG" 2>&1 < /dev/null &
    echo $! > "$FRONTEND_PID"
  )
  if ! is_running "$FRONTEND_PID"; then
    echo "frontend 进程未能启动，请查看 $FRONTEND_LOG"
    rm -f "$FRONTEND_PID"
    return 1
  fi
  wait_for_url "http://$UI_HOST:$UI_PORT/" "frontend"
  echo "frontend 已启动 (pid $(cat "$FRONTEND_PID"))"
}

stop_backend() {
  if is_running "$BACKEND_PID"; then
    PID="$(cat "$BACKEND_PID")"
    kill -- -"$PID" 2>/dev/null || kill "$PID" 2>/dev/null || true
    echo "backend 已停止 (pid $PID)"
  else
    echo "backend 未在运行"
  fi
  rm -f "$BACKEND_PID"
}

stop_frontend() {
  if is_running "$FRONTEND_PID"; then
    PID="$(cat "$FRONTEND_PID")"
    kill -- -"$PID" 2>/dev/null || kill "$PID" 2>/dev/null || true
    echo "frontend 已停止 (pid $PID)"
  else
    echo "frontend 未在运行"
  fi
  rm -f "$FRONTEND_PID"
}

show_status() {
  if is_running "$BACKEND_PID"; then
    echo "backend   运行中 (pid $(cat "$BACKEND_PID"))  http://$BACKEND_HOST:$BACKEND_PORT"
  else
    echo "backend   未运行"
  fi
  if is_running "$FRONTEND_PID"; then
    echo "frontend  运行中 (pid $(cat "$FRONTEND_PID"))  http://$UI_HOST:$UI_PORT"
  else
    echo "frontend  未运行"
  fi
}

show_logs() {
  local target="${1:-all}"
  if [ -n "$FOLLOW" ]; then
    case "$target" in
      backend)
        tail -f "$BACKEND_LOG" 2>/dev/null || echo "(无 backend 日志)"
        ;;
      frontend)
        tail -f "$FRONTEND_LOG" 2>/dev/null || echo "(无 frontend 日志)"
        ;;
      *)
        tail -f "$BACKEND_LOG" "$FRONTEND_LOG" 2>/dev/null || echo "(无日志)"
        ;;
    esac
    return
  fi

  case "$target" in
    backend)
      echo "=== backend.log ==="
      tail -n 40 "$BACKEND_LOG" 2>/dev/null || echo "(无日志)"
      ;;
    frontend)
      echo "=== frontend.log ==="
      tail -n 40 "$FRONTEND_LOG" 2>/dev/null || echo "(无日志)"
      ;;
    *)
      echo "=== backend.log ==="
      tail -n 30 "$BACKEND_LOG" 2>/dev/null || echo "(无日志)"
      echo
      echo "=== frontend.log ==="
      tail -n 30 "$FRONTEND_LOG" 2>/dev/null || echo "(无日志)"
      ;;
  esac
}

build_ui() {
  echo "构建前端生产包..."
  (cd "$ROOT/frontend/react-app" && npm run build)
  echo "构建完成 -> $ROOT/frontend/react-app/dist"
}

health() {
  local ok=1
  for url in "http://$BACKEND_HOST:$BACKEND_PORT/health" "http://$UI_HOST:$UI_PORT/"; do
    code="$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [ "$code" = "200" ]; then
      echo "OK    $url"
    else
      echo "FAIL  $url (code: ${code:-无响应})"
      ok=0
    fi
  done
  [ "$ok" = "1" ]
}

clean() {
  stop_backend
  stop_frontend
  rm -rf "$ROOT/frontend/react-app/dist"
  rm -f "$BACKEND_LOG" "$FRONTEND_LOG"
  echo "已清理 pid/日志/构建产物"
}

# ---- 解析子命令 ----
CMD="${1:-help}"
shift || true

# ---- 解析参数 ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      BACKEND_PORT="${2:?--port 缺少值}"
      shift 2
      ;;
    --host)
      BACKEND_HOST="${2:?--host 缺少值}"
      shift 2
      ;;
    --ui-port)
      UI_PORT="${2:?--ui-port 缺少值}"
      shift 2
      ;;
    --ui-host)
      UI_HOST="${2:?--ui-host 缺少值}"
      shift 2
      ;;
    -f | --follow)
      FOLLOW=1
      shift
      ;;
    backend | frontend)
      LOG_TARGET="$1"
      shift
      ;;
    *)
      echo "未知参数: $1"
      usage
      exit 1
      ;;
  esac
done

case "$CMD" in
  start)
    start_backend
    start_frontend
    ;;
  stop)
    stop_backend
    stop_frontend
    ;;
  restart)
    stop_backend
    stop_frontend
    sleep 1
    start_backend
    start_frontend
    ;;
  status)
    show_status
    ;;
  logs)
    show_logs "$LOG_TARGET"
    ;;
  backend)
    start_backend
    ;;
  frontend)
    start_frontend
    ;;
  build)
    build_ui
    ;;
  health)
    health
    ;;
  clean)
    clean
    ;;
  help | -h | --help)
    usage
    ;;
  *)
    echo "未知命令: $CMD"
    echo
    usage
    exit 1
    ;;
esac
