from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from threading import RLock
from typing import Dict, Protocol

from . import config
from .field_bus import get_field_bridge


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


_REAL_GPIO_CAPABLE = _running_on_raspberry_pi() and not config.SIMULATION_MODE

if _REAL_GPIO_CAPABLE:
    try:
        from gpiozero import OutputDevice
        _HAVE_GPIOZERO = True
    except Exception:  # pragma: no cover - dev fallback
        _HAVE_GPIOZERO = False
        OutputDevice = None  # type: ignore
else:
    _HAVE_GPIOZERO = False
    OutputDevice = None  # type: ignore


class _MockOutputDevice:
    def __init__(self, pin: int, active_high: bool = True, initial_value: bool = False) -> None:
        self.pin = pin
        self.active_high = active_high
        self.value = 1 if initial_value else 0

    def on(self) -> None:
        self.value = 1

    def off(self) -> None:
        self.value = 0

    def close(self) -> None:
        self.off()


@dataclass(frozen=True)
class RelayConfig:
    zone_pins: Dict[int, int]
    active_low: bool = True


class RelayBoardProtocol(Protocol):
    cfg: RelayConfig

    def set_zone(self, zone: int, on: bool) -> None: ...
    def all_off(self) -> None: ...
    def snapshot(self) -> Dict[int, bool]: ...
    def close(self) -> None: ...
    def backend_name(self) -> str: ...
    def diagnostics(self) -> dict: ...


class LocalZoneRelayBoard:
    def __init__(self, cfg: RelayConfig, force_mock: bool = False) -> None:
        self.cfg = cfg
        self.force_mock = force_mock
        self._lock = RLock()
        self._devices: Dict[int, object] = {}
        self._states: Dict[int, bool] = {zone: False for zone in cfg.zone_pins}
        self._build_devices()

    def _build_devices(self) -> None:
        use_real_gpio = _HAVE_GPIOZERO and _REAL_GPIO_CAPABLE and not self.force_mock
        for zone, pin in self.cfg.zone_pins.items():
            if use_real_gpio:
                dev = OutputDevice(pin=pin, active_high=not self.cfg.active_low, initial_value=False)
            else:
                dev = _MockOutputDevice(pin=pin, active_high=not self.cfg.active_low, initial_value=False)
            self._devices[zone] = dev

    def set_zone(self, zone: int, on: bool) -> None:
        with self._lock:
            dev = self._devices.get(zone)
            if dev is None:
                raise ValueError(f"Unknown zone {zone}")
            if on:
                dev.on()
            else:
                dev.off()
            self._states[zone] = bool(on)

    def all_off(self) -> None:
        with self._lock:
            for zone in list(self._devices):
                self.set_zone(zone, False)

    def snapshot(self) -> Dict[int, bool]:
        with self._lock:
            return dict(self._states)

    def close(self) -> None:
        with self._lock:
            for dev in self._devices.values():
                try:
                    dev.close()
                except Exception:
                    pass

    def backend_name(self) -> str:
        return 'mock' if self.force_mock or not (_HAVE_GPIOZERO and _REAL_GPIO_CAPABLE) else 'local_gpio'

    def diagnostics(self) -> dict:
        return {
            'backend': self.backend_name(),
            'gpiozero_available': _HAVE_GPIOZERO,
            'gpio_host_supported': _REAL_GPIO_CAPABLE,
            'active_low': self.cfg.active_low,
            'zone_pins': dict(self.cfg.zone_pins),
        }


class ESP32ZoneRelayBoard:
    def __init__(self, cfg: RelayConfig) -> None:
        self.cfg = cfg
        self._lock = RLock()
        self._states: Dict[int, bool] = {zone: False for zone in cfg.zone_pins}
        self._bridge = get_field_bridge()

    def set_zone(self, zone: int, on: bool) -> None:
        with self._lock:
            if zone not in self.cfg.zone_pins:
                raise ValueError(f"Unknown zone {zone}")
            response = self._bridge.set_zone(zone, on)
            if not response.get('ok'):
                raise RuntimeError(str(response.get('error') or 'ESP32 field controller rejected command'))
            if on:
                for known in self._states:
                    self._states[known] = False
            self._states[zone] = bool(on)

    def all_off(self) -> None:
        with self._lock:
            response = self._bridge.all_off()
            if not response.get('ok'):
                raise RuntimeError(str(response.get('error') or 'ESP32 field controller rejected all_off'))
            for zone in self._states:
                self._states[zone] = False

    def snapshot(self) -> Dict[int, bool]:
        with self._lock:
            remote = self._bridge.status()
            zones = remote.get('zones') if isinstance(remote.get('zones'), dict) else None
            if zones:
                for zone, state in zones.items():
                    try:
                        self._states[int(zone)] = bool(state)
                    except Exception:
                        continue
            return dict(self._states)

    def close(self) -> None:
        try:
            self._bridge.close()
        except Exception:
            pass

    def backend_name(self) -> str:
        return 'esp32_serial'

    def diagnostics(self) -> dict:
        payload = self._bridge.status()
        payload.setdefault('backend', self.backend_name())
        return payload


class ZoneRelayBoard:
    def __init__(self, cfg: RelayConfig) -> None:
        backend = config.HARDWARE_BACKEND
        if backend == 'ESP32_SERIAL':
            self._impl: RelayBoardProtocol = ESP32ZoneRelayBoard(cfg)
        elif backend == 'MOCK':
            self._impl = LocalZoneRelayBoard(cfg, force_mock=True)
        elif backend == 'LOCAL_GPIO':
            self._impl = LocalZoneRelayBoard(cfg, force_mock=not _HAVE_GPIOZERO)
        elif backend == 'AUTO':
            self._impl = ESP32ZoneRelayBoard(cfg) if config.ESP32_SERIAL_PORT_EXPLICIT else LocalZoneRelayBoard(cfg, force_mock=not _HAVE_GPIOZERO)
        else:
            self._impl = LocalZoneRelayBoard(cfg, force_mock=not _HAVE_GPIOZERO)
        self.cfg = self._impl.cfg

    def set_zone(self, zone: int, on: bool) -> None:
        return self._impl.set_zone(zone, on)

    def all_off(self) -> None:
        return self._impl.all_off()

    def snapshot(self) -> Dict[int, bool]:
        return self._impl.snapshot()

    def close(self) -> None:
        return self._impl.close()

    def backend_name(self) -> str:
        return self._impl.backend_name()

    def diagnostics(self) -> dict:
        return self._impl.diagnostics()
