from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass
from typing import Any

from . import config
from .field_bus import get_field_bridge
from .simulation import get_simulation_profile


def _running_on_raspberry_pi() -> bool:
    machine = platform.machine().lower()
    if machine.startswith(('arm', 'aarch64')):
        return True
    model_path = '/proc/device-tree/model'
    try:
        if os.path.exists(model_path):
            model = open(model_path, 'r', encoding='utf-8', errors='ignore').read().lower()
            return 'raspberry pi' in model
    except Exception:
        pass
    return False


_ENABLE_LOCAL_SENSOR_DRIVERS = _running_on_raspberry_pi() and not config.SIMULATION_MODE

if _ENABLE_LOCAL_SENSOR_DRIVERS:
    try:
        import board  # type: ignore
        import adafruit_dht  # type: ignore
        _HAVE_CIRCUITPY_DHT = True
    except Exception:
        board = None  # type: ignore
        adafruit_dht = None  # type: ignore
        _HAVE_CIRCUITPY_DHT = False

    try:
        import Adafruit_DHT  # type: ignore
        _HAVE_LEGACY_DHT = True
    except Exception:
        Adafruit_DHT = None  # type: ignore
        _HAVE_LEGACY_DHT = False

    try:
        from gpiozero import InputDevice, MCP3008
        _HAVE_GPIOZERO = True
    except Exception:
        InputDevice = None  # type: ignore
        MCP3008 = None  # type: ignore
        _HAVE_GPIOZERO = False
else:
    board = None  # type: ignore
    adafruit_dht = None  # type: ignore
    Adafruit_DHT = None  # type: ignore
    InputDevice = None  # type: ignore
    MCP3008 = None  # type: ignore
    _HAVE_CIRCUITPY_DHT = False
    _HAVE_LEGACY_DHT = False
    _HAVE_GPIOZERO = False


_BOARD_PIN_MAP = {
    4: lambda: board.D4 if board else None,
    17: lambda: board.D17 if board else None,
    27: lambda: board.D27 if board else None,
    22: lambda: board.D22 if board else None,
    5: lambda: board.D5 if board else None,
    6: lambda: board.D6 if board else None,
    13: lambda: board.D13 if board else None,
    19: lambda: board.D19 if board else None,
    26: lambda: board.D26 if board else None,
}


def _use_remote_sensors() -> bool:
    if config.SENSOR_BACKEND == 'ESP32':
        return True
    if config.SENSOR_BACKEND == 'LOCAL':
        return False
    return config.HARDWARE_BACKEND == 'ESP32_SERIAL'


@dataclass
class Telemetry:
    humidity: float | None
    temperature_c: float | None
    temperature_f: float | None
    soil_moisture_pct: float | None
    pressure_psi: float | None
    sensor_fault: bool = False
    mock: bool = False
    sensor_sources: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'humidity': self.humidity,
            'temperature_c': self.temperature_c,
            'temperature_f': self.temperature_f,
            'soil_moisture_pct': self.soil_moisture_pct,
            'pressure_psi': self.pressure_psi,
            'sensor_fault': self.sensor_fault,
            'mock': self.mock,
            'sensor_sources': self.sensor_sources or {},
        }


class DHTSensor:
    def __init__(self, enabled: bool = True, model: str | None = None, pin: int | None = None) -> None:
        self.enabled = enabled
        self.model = (model or config.DHT_MODEL).upper()
        self.pin = pin if pin is not None else config.DHT_PIN
        self._device = None
        self._remote = _use_remote_sensors()
        self._bridge = get_field_bridge() if self._remote else None
        self._sim = get_simulation_profile()
        if self._remote or self._sim.active() or not _ENABLE_LOCAL_SENSOR_DRIVERS:
            return
        if self.enabled and _HAVE_CIRCUITPY_DHT and board is not None:
            try:
                pin_factory = _BOARD_PIN_MAP.get(self.pin)
                board_pin = pin_factory() if pin_factory else None
                if board_pin is not None:
                    if self.model in {'DHT11'}:
                        self._device = adafruit_dht.DHT11(board_pin, use_pulseio=False)
                    else:
                        self._device = adafruit_dht.DHT22(board_pin, use_pulseio=False)
            except Exception:
                self._device = None

    def read(self) -> dict[str, Any]:
        if not self.enabled:
            return {'ok': False, 'disabled': True, 'humidity': None, 'temperature_c': None, 'temperature_f': None}

        if self._remote and self._bridge is not None:
            payload = self._bridge.read_sensors()
            if payload.get('ok') and payload.get('humidity') is not None and payload.get('temperature_c') is not None:
                temp_c = float(payload.get('temperature_c'))
                humidity = float(payload.get('humidity'))
                temp_f = payload.get('temperature_f')
                if temp_f is None:
                    temp_f = temp_c * 9.0 / 5.0 + 32.0
                return {
                    'ok': bool(payload.get('sensor_ok', True)),
                    'humidity': humidity,
                    'temperature_c': temp_c,
                    'temperature_f': float(temp_f),
                    'driver': payload.get('driver') or 'esp32_serial',
                    'remote': True,
                }

        if self._device is not None:
            try:
                humidity = float(self._device.humidity)
                temp_c = float(self._device.temperature)
                return {
                    'ok': True,
                    'humidity': humidity,
                    'temperature_c': temp_c,
                    'temperature_f': temp_c * 9.0 / 5.0 + 32.0,
                    'driver': 'adafruit_circuitpython_dht',
                }
            except Exception:
                pass

        if _HAVE_LEGACY_DHT:
            sensor = Adafruit_DHT.DHT11 if self.model == 'DHT11' else Adafruit_DHT.DHT22
            humidity, temp_c = Adafruit_DHT.read_retry(sensor, self.pin)
            if humidity is not None and temp_c is not None:
                return {
                    'ok': True,
                    'humidity': float(humidity),
                    'temperature_c': float(temp_c),
                    'temperature_f': float(temp_c) * 9.0 / 5.0 + 32.0,
                    'driver': 'Adafruit_DHT',
                }

        if self._sim.active():
            profile = self._sim.snapshot()
            return {
                'ok': True,
                'humidity': profile['humidity'],
                'temperature_c': profile['temperature_c'],
                'temperature_f': profile['temperature_f'],
                'driver': 'simulation_profile',
                'mock': True,
            }

        return {
            'ok': True,
            'humidity': 50.0,
            'temperature_c': 25.0,
            'temperature_f': 77.0,
            'driver': 'mock',
            'mock': True,
        }


class MoistureSensor:
    def __init__(self) -> None:
        self.mode = config.MOISTURE_MODE
        self._digital = None
        self._adc = None
        self._remote = _use_remote_sensors()
        self._bridge = get_field_bridge() if self._remote else None
        self._sim = get_simulation_profile()
        if self._remote or self._sim.active() or not _ENABLE_LOCAL_SENSOR_DRIVERS:
            return
        if _HAVE_GPIOZERO:
            try:
                if self.mode == 'ANALOG':
                    self._adc = MCP3008(channel=config.MOISTURE_ADC_CHANNEL)
                else:
                    self._digital = InputDevice(config.MOISTURE_PIN, pull_up=True)
            except Exception:
                self._digital = None
                self._adc = None

    def read_percent(self) -> float:
        if self._remote and self._bridge is not None:
            payload = self._bridge.read_sensors()
            remote_value = payload.get('soil_moisture_pct')
            if payload.get('ok') and remote_value is not None:
                return max(0.0, min(100.0, float(remote_value)))

        if self._sim.active():
            return float(self._sim.snapshot()['soil_moisture_pct'])

        if self.mode == 'ANALOG' and self._adc is not None:
            raw = float(self._adc.value)
        elif self._digital is not None:
            raw = 1.0 if self._digital.is_active else 0.0
        else:
            raw = 0.25 + (time.time() % 5.0) * 0.01

        lo = min(config.MOISTURE_DRY_CAL, config.MOISTURE_WET_CAL)
        hi = max(config.MOISTURE_DRY_CAL, config.MOISTURE_WET_CAL)
        if abs(hi - lo) < 1e-6:
            pct = raw * 100.0
        else:
            pct = (raw - lo) / (hi - lo) * 100.0
        return max(0.0, min(100.0, pct))


class PressureSensor:
    def __init__(self) -> None:
        self.mode = config.PRESSURE_MODE
        self._digital = None
        self._adc = None
        self._remote = _use_remote_sensors()
        self._bridge = get_field_bridge() if self._remote else None
        self._sim = get_simulation_profile()
        if self._remote or self._sim.active() or not _ENABLE_LOCAL_SENSOR_DRIVERS:
            return
        if _HAVE_GPIOZERO:
            try:
                if self.mode == 'DIGITAL':
                    self._digital = InputDevice(config.PRESSURE_PIN, pull_up=True)
                elif self.mode == 'ANALOG':
                    self._adc = MCP3008(channel=config.PRESSURE_ADC_CHANNEL)
            except Exception:
                self._digital = None
                self._adc = None

    def read_psi(self) -> float | None:
        if self._remote and self._bridge is not None:
            payload = self._bridge.read_sensors()
            remote_value = payload.get('pressure_psi')
            if payload.get('ok') and remote_value is not None:
                return float(remote_value)

        if self._sim.active():
            return float(self._sim.snapshot()['pressure_psi'])

        if self.mode == 'DIGITAL':
            if self._digital is None:
                return 45.0
            return 45.0 if self._digital.is_active else 0.0
        if self.mode == 'ANALOG':
            if self._adc is None:
                return 45.0
            raw = float(self._adc.value)
            return config.PRESSURE_LOW_PSI + raw * (config.PRESSURE_HIGH_PSI - config.PRESSURE_LOW_PSI)
        return 45.0


class SensorSuite:
    def __init__(self) -> None:
        self.dht = DHTSensor(enabled=config.DHT_ENABLED)
        self.moisture = MoistureSensor()
        self.pressure = PressureSensor()

    def read(self) -> Telemetry:
        dht = self.dht.read()
        moisture = self.moisture.read_percent()
        pressure = self.pressure.read_psi()
        mock = bool(dht.get('mock'))
        sensor_fault = not dht.get('ok', False)
        remote = _use_remote_sensors()
        sources = {
            'dht': str(dht.get('driver') or 'unknown'),
            'moisture': 'esp32_serial' if remote else ('simulation_profile' if get_simulation_profile().active() else config.MOISTURE_MODE.lower()),
            'pressure': 'esp32_serial' if remote and config.PRESSURE_MODE == 'ESP32' else ('simulation_profile' if get_simulation_profile().active() else config.PRESSURE_MODE.lower()),
        }
        return Telemetry(
            humidity=dht.get('humidity'),
            temperature_c=dht.get('temperature_c'),
            temperature_f=dht.get('temperature_f'),
            soil_moisture_pct=moisture,
            pressure_psi=pressure,
            sensor_fault=sensor_fault,
            mock=mock,
            sensor_sources=sources,
        )
