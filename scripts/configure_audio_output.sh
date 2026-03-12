#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${II_ENV_FILE:-.env}"
if [ "${ENV_FILE#/}" = "$ENV_FILE" ]; then
  ENV_FILE="$ROOT/$ENV_FILE"
fi

TARGET="${II_ASTRA_AUDIO_OUTPUT:-}"
if [ -z "$TARGET" ] && [ -f "$ENV_FILE" ]; then
  TARGET="$(awk -F= '/^II_ASTRA_AUDIO_OUTPUT=/{sub(/^[^=]*=/, "", $0); print $0; exit}' "$ENV_FILE")"
fi
TARGET="${TARGET:-AUTO}"
TARGET_UPPER="$(printf '%s' "$TARGET" | tr '[:lower:]' '[:upper:]')"

if [ "$TARGET_UPPER" = "AUTO" ] || [ "$TARGET_UPPER" = "" ]; then
  exit 0
fi

if [ "$TARGET_UPPER" != "HDMI" ]; then
  echo "Astra audio target '$TARGET_UPPER' is not handled by this helper yet. Leaving system audio unchanged."
  exit 0
fi

if command -v wpctl >/dev/null 2>&1; then
  sink_id="$(wpctl status 2>/dev/null | awk '
    /Sinks:/ { sinks=1; next }
    /Sources:/ { sinks=0 }
    sinks && tolower($0) ~ /hdmi/ {
      line=$0
      gsub(/[^0-9]/, " ", line)
      split(line, parts, /[[:space:]]+/)
      for (i in parts) {
        if (parts[i] ~ /^[0-9]+$/) { print parts[i]; exit }
      }
    }
  ')"
  if [ -n "$sink_id" ]; then
    wpctl set-default "$sink_id" >/dev/null 2>&1 || true
  fi
fi

if command -v pactl >/dev/null 2>&1; then
  sink_name="$(pactl list short sinks 2>/dev/null | awk 'tolower($2) ~ /hdmi/ { print $2; exit }')"
  if [ -n "$sink_name" ]; then
    pactl set-default-sink "$sink_name" >/dev/null 2>&1 || true
  fi
fi

if command -v amixer >/dev/null 2>&1; then
  amixer cset name='PCM Playback Route' 2 >/dev/null 2>&1 ||     amixer cset numid=3 2 >/dev/null 2>&1 || true
fi

exit 0
