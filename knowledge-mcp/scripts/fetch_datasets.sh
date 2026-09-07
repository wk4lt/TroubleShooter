#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/datasets/external"
mkdir -p "$TARGET"

clone_if_missing() {
  local repository="$1"
  local directory="$2"
  if [ -d "$TARGET/$directory/.git" ]; then
    echo "already present: $directory"
  else
    git clone --depth 1 "$repository" "$TARGET/$directory"
  fi
}

clone_if_missing https://github.com/o11y-dev/opentelemetry-skill.git opentelemetry-skill
clone_if_missing https://github.com/chayachandana/Incident-response-on-call-agent.git incident-response-on-call-agent
clone_if_missing https://github.com/atc-project/atc-react.git atc-react
clone_if_missing https://github.com/luduslibrum/awesome-playbooks.git awesome-playbooks

python3 "$ROOT/scripts/normalize_corpus.py"
echo "External corpora are downloaded and the phase-one corpus is normalized into knowledge/COMMON/."
