from __future__ import annotations

import json

from flask import Flask, jsonify, render_template, request, send_from_directory

from ingenious_irrigation import config
from ingenious_irrigation.astra import AstraAssistant
from ingenious_irrigation.controller import IrrigationController
from ingenious_irrigation.field_bus import find_serial_candidates, get_field_bridge
from ingenious_irrigation.notifications import Notifier
from ingenious_irrigation.schedule import ScheduleStore
from ingenious_irrigation.sensors import SensorSuite
from ingenious_irrigation.service import AutonomousService
from ingenious_irrigation.simulation import get_simulation_profile
from ingenious_irrigation.utils import tail_jsonl
from ingenious_irrigation.vision import VisionEngine
from ingenious_irrigation.voice import get_voice_service

app = Flask(__name__, static_folder=str(config.STATIC_DIR), template_folder=str(config.TEMPLATE_DIR))
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

schedule_store = ScheduleStore()
controller = IrrigationController(config.ZONE_PINS, active_low=config.ACTIVE_LOW)
sensors = SensorSuite()
vision = VisionEngine()
notifier = Notifier()
service = AutonomousService(controller, schedule_store, sensors, vision, notifier)
astra = AstraAssistant(controller, schedule_store, service)
simulation = get_simulation_profile()
voice = get_voice_service()
service.start()

UI_SETTINGS_FILE = config.DATA_ROOT / 'ui_settings.json'
DEFAULT_UI_SETTINGS = {
    'sprinkler': {
        'default_zone': 1,
        'default_minutes': 10,
        'start_time': '05:30',
        'soak_guard_enabled': True,
        'seasonal_blend_enabled': True,
        'quiet_hours_enabled': False,
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '06:00',
    },
    'ai': {
        'people_avoidance_enabled': True,
        'animal_deterrent_enabled': False,
        'animal_deterrent_start': '21:00',
        'animal_deterrent_end': '05:00',
        'animal_deterrent_distance_ft': 18,
        'intelligent_override_enabled': True,
        'intelligent_override_limit_pct': 12,
        'astra_enabled': True,
        'water_detection_enabled': True,
    },
}


def _deep_merge_dict(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_ui_settings() -> dict:
    if UI_SETTINGS_FILE.exists():
        try:
            stored = json.loads(UI_SETTINGS_FILE.read_text())
            return _deep_merge_dict(DEFAULT_UI_SETTINGS, stored)
        except Exception:
            pass
    save_ui_settings(DEFAULT_UI_SETTINGS)
    return json.loads(json.dumps(DEFAULT_UI_SETTINGS))


def save_ui_settings(payload: dict) -> dict:
    merged = _deep_merge_dict(DEFAULT_UI_SETTINGS, payload or {})
    UI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_FILE.write_text(json.dumps(merged, indent=2))
    return merged


ui_settings = load_ui_settings()


def _int_arg(value: object, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _zone_defaults(zone: int) -> dict:
    zones = schedule_store.snapshot().get('zones', {})
    return zones.get(str(zone), {'minutes': 10, 'enabled': True, 'start_time': '05:00', 'frequency': 'daily'})


@app.after_request
def _no_cache(resp):
    ct = resp.headers.get('Content-Type', '')
    if 'text/html' in ct or 'application/json' in ct:
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@app.get('/')
def dashboard():
    return render_template('dashboard.html')


@app.get('/sprinkler-settings')
def sprinkler_settings_page():
    return render_template('sprinkler_settings.html')


@app.get('/ai-settings')
def ai_settings_page():
    return render_template('ai_settings.html')


@app.get('/details')
def details_page():
    return render_template('details.html')


@app.get('/health')
def health():
    return jsonify({
        'ok': True,
        'service': service.status(),
        'controller': controller.status(),
        'hardware': controller.hardware_status(),
        'simulation': simulation.snapshot(),
        'serial_candidates': find_serial_candidates(),
        'voice': voice.status(),
        'config': {
            'data_root': str(config.DATA_ROOT),
            'hardware_backend': config.HARDWARE_BACKEND,
            'sensor_backend': config.SENSOR_BACKEND,
            'zone_ids': config.ZONE_IDS,
            'simulation_mode': config.SIMULATION_MODE,
            'simulate_field_io': config.SIMULATE_FIELD_IO,
            'simulate_camera': config.SIMULATE_CAMERA,
            'astra_name': config.ASTRA_NAME,
            'astra_wake_word': config.ASTRA_WAKE_WORD,
            'astra_audio_output': config.ASTRA_AUDIO_OUTPUT,
        },
    })


@app.get('/favicon.ico')
def favicon():
    path = config.STATIC_DIR / 'favicon.ico'
    if path.exists():
        return send_from_directory(str(config.STATIC_DIR), 'favicon.ico')
    return ('', 204)


@app.get('/api/schedule')
def api_get_schedule():
    return jsonify(schedule_store.snapshot())


@app.post('/api/schedule/update')
def api_update_schedule():
    payload = request.get_json(silent=True) or {}
    zone = _int_arg(payload.get('zone', 1), 1, minimum=1)
    updates = {
        'minutes': payload.get('minutes'),
        'enabled': payload.get('enabled'),
        'astra_control_enabled': payload.get('astra_control_enabled'),
        'start_time': payload.get('start_time'),
        'frequency': payload.get('frequency'),
        'every_x_days': payload.get('every_x_days'),
        'days_of_week': payload.get('days_of_week'),
    }
    updated = schedule_store.update_zone(zone, **updates)
    return jsonify({'ok': True, 'zone': zone, 'config': updated})


@app.post('/api/zone/<int:zone>/run')
def api_run_zone(zone: int):
    payload = request.get_json(silent=True) or {}
    defaults = _zone_defaults(zone)
    minutes = _int_arg(payload.get('minutes', defaults.get('minutes', 10)), int(defaults.get('minutes', 10)), minimum=1, maximum=240)
    result = controller.start_zone(zone, minutes, reason='api_manual_run')
    code = 200 if result.get('ok') else 400
    return jsonify(result), code


@app.post('/api/zone/<int:zone>/stop')
def api_stop_zone(zone: int):
    result = controller.stop_zone(zone, reason='api_manual_stop')
    code = 200 if result.get('ok') else 400
    return jsonify(result), code


@app.get('/api/system/status')
def api_system_status():
    return jsonify({
        'controller': controller.status(),
        'service': service.status(),
        'telemetry': service.latest_telemetry(),
        'hardware': controller.hardware_status(),
        'simulation': simulation.snapshot(),
        'serial_candidates': find_serial_candidates(),
        'voice': voice.status(),
    })


@app.get('/api/telemetry')
def api_telemetry():
    default_zone = config.ZONE_IDS[0] if config.ZONE_IDS else None
    return jsonify(service.analyze_once(zone=default_zone))


@app.get('/api/field/ping')
def api_field_ping():
    return jsonify(get_field_bridge().ping())


@app.get('/api/field/status')
def api_field_status():
    payload = get_field_bridge().status()
    payload['controller_backend'] = controller.status().get('backend')
    payload['serial_candidates'] = find_serial_candidates()
    return jsonify(payload)


@app.get('/api/field/sensors')
def api_field_sensors():
    return jsonify(get_field_bridge().read_sensors())


@app.get('/api/serial/candidates')
def api_serial_candidates():
    return jsonify({'ok': True, 'ports': find_serial_candidates()})


@app.get('/api/simulation')
def api_get_simulation():
    return jsonify({
        'ok': True,
        'active': simulation.active(),
        'profile': simulation.snapshot(),
        'presets': simulation.presets(),
        'hardware_bookmarks': [
            'Confirm the exact USB serial path when the ESP32 is connected.',
            'Bench-test relay logic with a real valve or indicator load.',
            'Add and calibrate the real camera feed before enabling autonomy.',
            'Install real soil moisture and pressure sensors before production.',
            'Add a USB microphone when you want true wake-word voice input on the Pi.',
        ],
    })


@app.post('/api/simulation')
def api_update_simulation():
    payload = request.get_json(silent=True) or {}
    updates = {
        'scenario': payload.get('scenario'),
        'people_present': payload.get('people_present', payload.get('people')),
        'humidity': payload.get('humidity'),
        'temperature_c': payload.get('temperature_c'),
        'soil_moisture_pct': payload.get('soil_moisture_pct'),
        'pressure_psi': payload.get('pressure_psi'),
    }
    profile = simulation.update(**updates)
    default_zone = config.ZONE_IDS[0] if config.ZONE_IDS else None
    analysis = service.analyze_once(zone=default_zone)
    return jsonify({'ok': True, 'profile': profile, 'analysis': analysis})


@app.post('/api/zone/<int:zone>/analyze')
def api_analyze_zone(zone: int):
    return jsonify(service.analyze_once(zone=zone))


@app.get('/api/decisions')
def api_decisions():
    limit = _int_arg(request.args.get('limit', 100), 100, minimum=1, maximum=500)
    return jsonify(service.recent_decisions(limit=limit))


@app.get('/api/incidents')
def api_incidents():
    limit = _int_arg(request.args.get('limit', 100), 100, minimum=1, maximum=500)
    return jsonify(tail_jsonl(config.INCIDENT_LOG, limit=limit))


@app.get('/api/astra/profile')
def api_astra_profile():
    return jsonify({
        'ok': True,
        **astra.profile(),
        'voice': voice.status(),
    })


@app.post('/api/astra/speak')
def api_astra_speak():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text') or '').strip()
    context = str(payload.get('context') or 'general').strip() or 'general'
    result = voice.speak(text, context=context)
    return jsonify(result), (200 if result.get('ok') else 400)


@app.post('/astra/chat')
@app.post('/chat')
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get('message') or '').strip()
    reply = astra.respond(message)
    return jsonify({'reply': reply})


@app.get('/api/astra/brief')
def api_astra_brief():
    return jsonify({'ok': True, **astra.briefing()})


@app.get('/api/settings')
def api_get_settings():
    global ui_settings
    ui_settings = load_ui_settings()
    return jsonify({'ok': True, 'settings': ui_settings})


@app.post('/api/settings/sprinkler')
def api_save_sprinkler_settings():
    global ui_settings
    payload = request.get_json(silent=True) or {}
    ui_settings = save_ui_settings({'sprinkler': payload, 'ai': ui_settings.get('ai', {})})
    return jsonify({'ok': True, 'settings': ui_settings})


@app.post('/api/settings/ai')
def api_save_ai_settings():
    global ui_settings
    payload = request.get_json(silent=True) or {}
    ui_settings = save_ui_settings({'sprinkler': ui_settings.get('sprinkler', {}), 'ai': payload})
    return jsonify({'ok': True, 'settings': ui_settings})


if __name__ == '__main__':
    app.run(host=config.APP_HOST, port=config.APP_PORT, debug=False)
