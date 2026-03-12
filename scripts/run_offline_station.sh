#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f .env ]; then
  cp .env.offline .env
fi

export II_ENV_FILE=.env

./scripts/configure_audio_output.sh

python app.py
