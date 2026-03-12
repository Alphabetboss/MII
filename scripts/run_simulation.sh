#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [[ -f .env.simulation ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.simulation
  set +a
fi
exec python3 app.py
