from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from . import config
from .utils import iso_utc, read_json, write_json


@dataclass(frozen=True)
class ScenarioPreset:
    name: str
    label: str
    description: str
    humidity: float
    temperature_c: float
    soil_moisture_pct: float
    pressure_psi: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "humidity": self.humidity,
            "temperature_c": self.temperature_c,
            "temperature_f": round(self.temperature_c * 9.0 / 5.0 + 32.0, 1),
            "soil_moisture_pct": self.soil_moisture_pct,
            "pressure_psi": self.pressure_psi,
        }


_PRESETS: dict[str, ScenarioPreset] = {
    "healthy": ScenarioPreset(
        name="healthy",
        label="Healthy",
        description="Balanced turf with normal demand.",
        humidity=52.0,
        temperature_c=24.0,
        soil_moisture_pct=42.0,
        pressure_psi=46.0,
    ),
    "dry": ScenarioPreset(
        name="dry",
        label="Dry",
        description="Hot, thirsty turf that needs more runtime.",
        humidity=26.0,
        temperature_c=33.0,
        soil_moisture_pct=14.0,
        pressure_psi=45.0,
    ),
    "yellow": ScenarioPreset(
        name="yellow",
        label="Yellowing",
        description="Early stress or uneven watering pattern.",
        humidity=41.0,
        temperature_c=30.0,
        soil_moisture_pct=26.0,
        pressure_psi=44.0,
    ),
    "water": ScenarioPreset(
        name="water",
        label="Standing Water",
        description="Oversaturated zone or possible leak / drainage issue.",
        humidity=88.0,
        temperature_c=20.0,
        soil_moisture_pct=84.0,
        pressure_psi=68.0,
    ),
}


class SimulationProfileStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._path = config.DATA_DIR / 'simulation_profile.json'
        self._profile = self._load()

    def active(self) -> bool:
        return bool(
            config.SIMULATION_MODE
            or config.SIMULATE_CAMERA
            or config.SIMULATE_FIELD_IO
            or config.HARDWARE_BACKEND == 'MOCK'
        )

    def presets(self) -> list[dict[str, Any]]:
        return [preset.as_dict() for preset in _PRESETS.values()]

    def _default(self) -> dict[str, Any]:
        preset = _PRESETS.get(config.SIMULATE_CAMERA_SCENARIO, _PRESETS['healthy'])
        return {
            'scenario': preset.name,
            'scenario_label': preset.label,
            'description': preset.description,
            'people_present': bool(config.SIMULATE_PEOPLE),
            'humidity': preset.humidity,
            'temperature_c': preset.temperature_c,
            'temperature_f': round(preset.temperature_c * 9.0 / 5.0 + 32.0, 1),
            'soil_moisture_pct': preset.soil_moisture_pct,
            'pressure_psi': preset.pressure_psi,
            'updated_at': iso_utc(),
            'camera_enabled': bool(config.SIMULATE_CAMERA),
            'field_io_enabled': bool(config.SIMULATE_FIELD_IO or config.HARDWARE_BACKEND == 'MOCK'),
            'autonomy_enabled': bool(config.AUTONOMY_ENABLED),
            'notes': [
                'Simulation mode uses safe synthetic camera frames and fake sensor values.',
                'Switch to real hardware later by disabling the simulation flags in .env.',
            ],
        }

    def _normalize(self, raw: dict[str, Any] | None) -> dict[str, Any]:
        current = dict(self._default())
        if isinstance(raw, dict):
            current.update(raw)
        scenario = str(current.get('scenario', 'healthy')).strip().lower()
        if scenario not in _PRESETS:
            scenario = 'healthy'
        preset = _PRESETS[scenario]
        current['scenario'] = scenario
        current['scenario_label'] = preset.label
        current['description'] = preset.description

        def _num(key: str, fallback: float, lo: float, hi: float) -> float:
            try:
                value = float(current.get(key, fallback))
            except Exception:
                value = fallback
            return round(max(lo, min(hi, value)), 2)

        current['people_present'] = bool(current.get('people_present', False))
        current['humidity'] = _num('humidity', preset.humidity, 0.0, 100.0)
        current['temperature_c'] = _num('temperature_c', preset.temperature_c, -20.0, 65.0)
        current['temperature_f'] = round(current['temperature_c'] * 9.0 / 5.0 + 32.0, 2)
        current['soil_moisture_pct'] = _num('soil_moisture_pct', preset.soil_moisture_pct, 0.0, 100.0)
        current['pressure_psi'] = _num('pressure_psi', preset.pressure_psi, 0.0, 120.0)
        current['updated_at'] = str(current.get('updated_at') or iso_utc())
        current['camera_enabled'] = bool(current.get('camera_enabled', config.SIMULATE_CAMERA))
        current['field_io_enabled'] = bool(current.get('field_io_enabled', config.SIMULATE_FIELD_IO or config.HARDWARE_BACKEND == 'MOCK'))
        current['autonomy_enabled'] = bool(current.get('autonomy_enabled', config.AUTONOMY_ENABLED))
        notes = current.get('notes')
        if isinstance(notes, list):
            current['notes'] = [str(item) for item in notes if str(item).strip()]
        else:
            current['notes'] = list(self._default()['notes'])
        return current

    def _load(self) -> dict[str, Any]:
        with self._lock:
            raw = read_json(self._path, None)
            self._profile = self._normalize(raw)
            write_json(self._path, self._profile)
            return dict(self._profile)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._profile)

    def update(self, **updates: Any) -> dict[str, Any]:
        with self._lock:
            merged = dict(self._profile)
            scenario_value = updates.get('scenario')
            if scenario_value is not None:
                scenario_name = str(scenario_value).strip().lower()
                preset = _PRESETS.get(scenario_name, _PRESETS['healthy'])
                merged.update({
                    'scenario': preset.name,
                    'humidity': preset.humidity,
                    'temperature_c': preset.temperature_c,
                    'soil_moisture_pct': preset.soil_moisture_pct,
                    'pressure_psi': preset.pressure_psi,
                })
            for key, value in updates.items():
                if value is not None:
                    merged[key] = value
            merged['updated_at'] = iso_utc()
            self._profile = self._normalize(merged)
            write_json(self._path, self._profile)
            return dict(self._profile)


_SIMULATION: SimulationProfileStore | None = None


def get_simulation_profile() -> SimulationProfileStore:
    global _SIMULATION
    if _SIMULATION is None:
        _SIMULATION = SimulationProfileStore()
    return _SIMULATION
