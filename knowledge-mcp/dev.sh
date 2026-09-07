#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PYTHON="${KNOWLEDGE_PYTHON:-python3.11}"
HOST="${KNOWLEDGE_MCP_HOST:-127.0.0.1}"
PORT="${KNOWLEDGE_MCP_PORT:-8010}"

case "${1:-help}" in
  setup)
    "$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Knowledge MCP requires Python 3.11+"'
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install -e "$ROOT"
    ;;
  ingest)
    cd "$ROOT"
    "$VENV/bin/python" scripts/ingest.py
    ;;
  serve)
    cd "$ROOT"
    MCP_HOST="$HOST" MCP_PORT="$PORT" "$VENV/bin/python" -m app.server
    ;;
  eval)
    cd "$ROOT"
    "$VENV/bin/python" scripts/eval_retrieval.py
    ;;
  fetch-datasets)
    "$ROOT/scripts/fetch_datasets.sh"
    ;;
  *)
    echo "Usage: ./knowledge-mcp/dev.sh {setup|ingest|serve|eval|fetch-datasets}"
    ;;
esac
