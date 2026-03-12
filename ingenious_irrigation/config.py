from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file() -> None:
    env_hint = os.getenv("II_ENV_FILE", ".env").strip() or ".env"
    env_path = Path(env_hint)
    if not env_path.is_absolute():
        env_path = (BASE_DIR / env_path).resolve()
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env_file()
DATA_ROOT = Path(os.getenv("II_DATA_ROOT", str(BASE_DIR))).expanduser().resolve()
DATA_DIR = DATA_ROOT / "data"
LOG_DIR = DATA_ROOT / "logs"
SNAPSHOT_DIR = DATA_ROOT / "snapshots"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
FIRMWARE_DIR = BASE_DIR / "firmware"

for _path in (DATA_DIR, LOG_DIR, SNAPSHOT_DIR, TEMPLATE_DIR, STATIC_DIR, FIRMWARE_DIR):
    _path.mkdir(parents=True, exist_ok=True)

SCHEDULE_FILE = DATA_DIR / "schedule.json"
STATUS_FILE = DATA_DIR / "status.json"
TELEMETRY_FILE = DATA_DIR / "telemetry.json"
DECISION_LOG = LOG_DIR / "decision_log.jsonl"
INCIDENT_LOG = LOG_DIR / "incident_log.jsonl"
NOTIFICATION_LOG = LOG_DIR / "notifications.log"

API_KEY = os.getenv("II_API_KEY", "dev-key")
APP_HOST = os.getenv("II_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("II_PORT", "5051"))
POLL_SECONDS = float(os.getenv("II_POLL_SECONDS", "15"))
AUTONOMY_ENABLED = os.getenv("II_AUTONOMY_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
DEFAULT_LOCATION = os.getenv("II_LOCATION", "Unknown yard")


ASTRA_NAME = os.getenv("II_ASTRA_NAME", "Astra").strip() or "Astra"
ASTRA_WAKE_WORD = os.getenv("II_ASTRA_WAKE_WORD", ASTRA_NAME).strip() or ASTRA_NAME
ASTRA_CATCH_PHRASE = os.getenv(
    "II_ASTRA_CATCH_PHRASE",
    "Astra online. Yard intelligence standing by.",
).strip() or "Astra online. Yard intelligence standing by."
ASTRA_PERSONALITY = os.getenv(
    "II_ASTRA_PERSONALITY",
    "futuristic, witty, confident, pro technician, intelligent",
).strip()
ASTRA_STATION_STYLE = os.getenv("II_ASTRA_STATION_STYLE", "docked_station").strip().lower()
ASTRA_LOCAL_VOICE_ENABLED = os.getenv("II_ASTRA_LOCAL_VOICE", "1").strip().lower() not in {"0", "false", "no"}
ASTRA_LOCAL_VOICE_ENGINE = os.getenv("II_ASTRA_LOCAL_VOICE_ENGINE", "AUTO").strip().upper()
ASTRA_ALLOW_BROWSER_TTS = os.getenv("II_ASTRA_ALLOW_BROWSER_TTS", "0").strip().lower() in {"1", "true", "yes"}
ASTRA_VOICE_NAME = os.getenv("II_ASTRA_VOICE_NAME", "female").strip()
ASTRA_VOICE_RATE_WPM = int(os.getenv("II_ASTRA_VOICE_RATE_WPM", "165"))
ASTRA_VOICE_PITCH = int(os.getenv("II_ASTRA_VOICE_PITCH", "58"))
ASTRA_AUDIO_OUTPUT = os.getenv("II_ASTRA_AUDIO_OUTPUT", "AUTO").strip().upper()
ASTRA_TTS_PROVIDER = os.getenv("II_ASTRA_TTS_PROVIDER", "AUTO").strip().upper()
ELEVENLABS_API_KEY = os.getenv("II_ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.getenv("II_ELEVENLABS_VOICE_ID", "Rachel").strip() or "Rachel"
ELEVENLABS_MODEL_ID = os.getenv("II_ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip() or "eleven_multilingual_v2"
ELEVENLABS_OUTPUT_FORMAT = os.getenv("II_ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128").strip() or "mp3_44100_128"
WATER_DETECTION_MIN_MOTION_RATIO = float(os.getenv("II_WATER_DETECTION_MIN_MOTION_RATIO", "0.01"))
WATER_DETECTION_MIN_WATER_RATIO = float(os.getenv("II_WATER_DETECTION_MIN_WATER_RATIO", "0.003"))
WATER_DETECTION_SCORE_THRESHOLD = float(os.getenv("II_WATER_DETECTION_SCORE_THRESHOLD", "0.35"))
WATER_DETECTION_CONSECUTIVE = int(os.getenv("II_WATER_DETECTION_CONSECUTIVE", "2"))
MASTER_VALVE_ZONE = int(os.getenv("II_MASTER_VALVE_ZONE", "0"))

SIMULATION_MODE = os.getenv("II_SIMULATION_MODE", "0").strip().lower() in {"1", "true", "yes"}
SIMULATE_CAMERA = os.getenv("II_CAMERA_SIMULATE", "1" if SIMULATION_MODE else "0").strip().lower() in {"1", "true", "yes"}
SIMULATE_CAMERA_SCENARIO = os.getenv("II_CAMERA_SIM_SCENARIO", "healthy").strip().lower()
SIMULATE_PEOPLE = os.getenv("II_CAMERA_SIM_PEOPLE", "0").strip().lower() in {"1", "true", "yes"}
SIMULATE_FIELD_IO = os.getenv("II_FIELD_IO_SIMULATE", "1" if SIMULATION_MODE else "0").strip().lower() in {"1", "true", "yes"}

CAMERA_INDEX = int(os.getenv("II_CAMERA_INDEX", "0"))
CAMERA_URL = os.getenv("II_CAMERA_URL", "").strip()
CAMERA_WIDTH = int(os.getenv("II_CAMERA_WIDTH", "1280"))
CAMERA_HEIGHT = int(os.getenv("II_CAMERA_HEIGHT", "720"))
CAMERA_TIMEOUT = float(os.getenv("II_CAMERA_TIMEOUT", "4"))
YOLO_MODEL_PATH = os.getenv("II_YOLO_MODEL", "").strip()
YOLO_CONF = float(os.getenv("II_YOLO_CONF", "0.25"))

PEOPLE_DETECTION_ENABLED = os.getenv("II_PEOPLE_DETECTION", "1").strip().lower() not in {"0", "false", "no"}
PEOPLE_MIN_CONFIDENCE = float(os.getenv("II_PEOPLE_MIN_CONF", "0.4"))

HARDWARE_BACKEND = os.getenv("II_HARDWARE_BACKEND", "AUTO").strip().upper()
SENSOR_BACKEND = os.getenv("II_SENSOR_BACKEND", "AUTO").strip().upper()
STRICT_FIELD_IO = os.getenv("II_STRICT_FIELD_IO", "0").strip().lower() in {"1", "true", "yes"}

ESP32_SERIAL_PORT_EXPLICIT = os.getenv("II_ESP32_SERIAL_PORT", "").strip()
ESP32_SERIAL_PORT = ESP32_SERIAL_PORT_EXPLICIT or "/dev/ttyACM0"
ESP32_BAUD = int(os.getenv("II_ESP32_BAUD", "115200"))
ESP32_TIMEOUT = float(os.getenv("II_ESP32_TIMEOUT", "2.0"))
ESP32_BOOT_WAIT = float(os.getenv("II_ESP32_BOOT_WAIT", "2.0"))
ESP32_DHT_PIN = int(os.getenv("II_ESP32_DHT_PIN", "4"))
ESP32_RELAY_PIN = int(os.getenv("II_ESP32_RELAY_PIN", "26"))
ESP32_RELAY_ACTIVE_LOW = os.getenv("II_ESP32_RELAY_ACTIVE_LOW", "1").strip().lower() not in {"0", "false", "no"}
ESP32_PROTOCOL = os.getenv("II_ESP32_PROTOCOL", "serial_line_v1").strip().lower()

DHT_MODEL = os.getenv("II_DHT_MODEL", "DHT11").strip().upper()
DHT_PIN = int(os.getenv("II_DHT_PIN", "4"))
DHT_ENABLED = os.getenv("II_DHT_ENABLED", "1").strip().lower() not in {"0", "false", "no"}

MOISTURE_MODE = os.getenv("II_MOISTURE_MODE", "DIGITAL").strip().upper()
MOISTURE_PIN = int(os.getenv("II_MOISTURE_PIN", "17"))
MOISTURE_ADC_CHANNEL = int(os.getenv("II_MOISTURE_ADC_CHANNEL", "0"))
MOISTURE_DRY_CAL = float(os.getenv("II_MOISTURE_DRY_CAL", "0.0"))
MOISTURE_WET_CAL = float(os.getenv("II_MOISTURE_WET_CAL", "1.0"))

PRESSURE_MODE = os.getenv("II_PRESSURE_MODE", "MOCK").strip().upper()
PRESSURE_PIN = int(os.getenv("II_PRESSURE_PIN", "27"))
PRESSURE_ADC_CHANNEL = int(os.getenv("II_PRESSURE_ADC_CHANNEL", "1"))
PRESSURE_LOW_PSI = float(os.getenv("II_PRESSURE_LOW_PSI", "8.0"))
PRESSURE_HIGH_PSI = float(os.getenv("II_PRESSURE_HIGH_PSI", "90.0"))

ACTIVE_LOW = os.getenv("II_ACTIVE_LOW", "1").strip().lower() not in {"0", "false", "no"}
DEFAULT_ZONE_PINS = {1: 17, 2: 27, 3: 22, 4: 5, 5: 6, 6: 13}


def parse_zone_pins(raw: str | None = None) -> Dict[int, int]:
    """Parse II_ZONE_PINS='1:17,2:27,...' into a zone->BCM pin map."""
    text = (raw if raw is not None else os.getenv("II_ZONE_PINS", "")).strip()
    if not text:
        return dict(DEFAULT_ZONE_PINS)
    parsed: Dict[int, int] = {}
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        zone_s, pin_s = chunk.split(":", 1)
        try:
            parsed[int(zone_s.strip())] = int(pin_s.strip())
        except ValueError:
            continue
    return parsed or dict(DEFAULT_ZONE_PINS)


def parse_zone_ids(raw: str | None = None) -> List[int]:
    text = (raw if raw is not None else os.getenv("II_ZONE_IDS", "")).strip()
    if not text:
        return []
    out: List[int] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(int(chunk))
        except ValueError:
            continue
    deduped = sorted({zone for zone in out if zone > 0})
    return deduped


_EXPLICIT_ZONE_IDS = parse_zone_ids()
_raw_zone_pins = os.getenv("II_ZONE_PINS", "").strip()
if _raw_zone_pins:
    ZONE_PINS = parse_zone_pins(_raw_zone_pins)
elif _EXPLICIT_ZONE_IDS:
    # Synthetic logical map for remote controllers like the ESP32 field board.
    ZONE_PINS = {zone: zone for zone in _EXPLICIT_ZONE_IDS}
else:
    ZONE_PINS = parse_zone_pins()

ZONE_IDS = _EXPLICIT_ZONE_IDS or sorted(ZONE_PINS)
