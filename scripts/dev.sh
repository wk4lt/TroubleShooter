#!/usr/bin/env bash
#
# AI Agent Platform 开发服务管理脚本
#
# 用法:
#   scripts/dev.sh start     启动 backend + frontend
#   scripts/dev.sh stop      停止 backend + frontend
#   scripts/dev.sh restart   重启
#   scripts/dev.sh status    查看状态
#   scripts/dev.sh logs      查看日志(尾部)
#   scripts/dev.sh backend   只启动 backend
#   scripts/dev.sh frontend  只启动 frontend
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

BACKEND_PID="$RUN_DIR/backend.pid"
FRONTEND_PID="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

is_running() {
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

start_backend() {
  if is_running "$BACKEND_PID"; then
    echo "backend 已在运行 (pid $(cat "$BACKEND_PID"))"
    return
  fi
  echo "启动 backend  -> http://127.0.0.1:8000"
  (
    cd "$ROOT/backend"
    setsid python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
      >> "$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! > "$BACKEND_PID"
  )
  sleep 1
  echo "backend 已启动 (pid $(cat "$BACKEND_PID"))"
}

start_frontend() {
  if is_running "$FRONTEND_PID"; then
    echo "frontend 已在运行 (pid $(cat "$FRONTEND_PID"))"
    return
  fi
  echo "启动 frontend -> http://127.0.0.1:5173"
  (
    cd "$ROOT/frontend/react-app"
    setsid npm run dev -- --host 127.0.0.1 \
      >> "$FRONTEND_LOG" 2>&1 < /dev/null &
    echo $! > "$FRONTEND_PID"
  )
  sleep 1
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
    echo "backend  运行中 (pid $(cat "$BACKEND_PID"))"
  else
    echo "backend  未运行"
  fi
  if is_running "$FRONTEND_PID"; then
    echo "frontend 运行中 (pid $(cat "$FRONTEND_PID"))"
  else
    echo "frontend 未运行"
  fi
}

show_logs() {
  echo "=== backend.log ==="
  tail -n 30 "$BACKEND_LOG" 2>/dev/null || echo "(无日志)"
  echo
  echo "=== frontend.log ==="
  tail -n 30 "$FRONTEND_LOG" 2>/dev/null || echo "(无日志)"
}

usage() {
  sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
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
    show_logs
    ;;
  backend)
    start_backend
    ;;
  frontend)
    start_frontend
    ;;
  *)
    usage
    ;;
esac
