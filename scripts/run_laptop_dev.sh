#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

# Ensure dependencies are installed.  Without this, running python may raise
# ModuleNotFoundError (e.g., missing Flask).  Installing requirements
# here prevents that and keeps the environment fresh.  You can remove
# '--upgrade pip' if you prefer to retain the default pip version.
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null

export II_ENV_FILE=.env.laptop_dev

python app.py
