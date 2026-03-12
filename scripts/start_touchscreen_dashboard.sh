#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://localhost:5051}"

if ! command -v chromium-browser >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
  echo "Chromium is not installed. Install it first: sudo apt install chromium-browser"
  exit 1
fi

BROWSER="chromium-browser"
if ! command -v chromium-browser >/dev/null 2>&1; then
  BROWSER="chromium"
fi

"$BROWSER"   --app="$URL"   --start-fullscreen   --kiosk   --noerrdialogs   --disable-infobars   --check-for-update-interval=31536000
