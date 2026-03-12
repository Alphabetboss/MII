#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.offline .env
  echo "Created .env from .env.offline. Edit serial path and hardware settings before going live."
fi

if ! command -v espeak-ng >/dev/null 2>&1 && ! command -v espeak >/dev/null 2>&1; then
  echo "Offline Astra voice note: install espeak-ng for the best local Pi voice."
  echo "Debian/Raspberry Pi OS: sudo apt-get update && sudo apt-get install -y espeak-ng libespeak1"
fi

echo "Done. Start with: source .venv/bin/activate && ./scripts/run_offline_station.sh"
