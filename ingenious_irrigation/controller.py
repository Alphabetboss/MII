from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from .gpio import RelayConfig, ZoneRelayBoard
from .utils import iso_utc


@dataclass
class ActiveRun:
    zone: int
    started_at: float
    ends_at: float
    reason: str
    requested_minutes: int
    timer: threading.Timer


class IrrigationController:
    def __init__(self, zone_pins: dict[int, int], active_low: bool = True) -> None:
        self.board = ZoneRelayBoard(RelayConfig(zone_pins=zone_pins, active_low=active_low))
        self._lock = threading.RLock()
        self._active: Optional[ActiveRun] = None
        self._last_stop_reason = "idle"

    def _epoch_to_iso(self, value: float | None) -> str | None:
        if value is None:
            return None
        return iso_utc(datetime.fromtimestamp(value, tz=timezone.utc))

    def start_zone(self, zone: int, minutes: int, reason: str = "manual") -> dict[str, Any]:
        minutes = max(0, int(minutes))
        with self._lock:
            if minutes <= 0:
                return {"ok": False, "error": "minutes must be > 0"}
            if zone not in self.board.cfg.zone_pins:
                return {"ok": False, "error": f"unknown zone {zone}"}

            try:
                # Make sure only one zone is active at a time.
                self._cancel_active_locked("switching_zones")
                self.board.all_off()
                self.board.set_zone(zone, True)
            except Exception as exc:
                self._last_stop_reason = f"hardware_error:{exc}"
                return {"ok": False, "error": f"hardware backend failed to start zone {zone}: {exc}"}

            seconds = float(minutes * 60)
            timer = threading.Timer(seconds, self._timer_stop, args=(zone, "completed"))
            timer.daemon = True
            timer.start()
            now = time.time()
            self._active = ActiveRun(
                zone=zone,
                started_at=now,
                ends_at=now + seconds,
                reason=reason,
                requested_minutes=minutes,
                timer=timer,
            )
            return {"ok": True, "zone": zone, "minutes": minutes, "reason": reason, "backend": self.board.backend_name()}

    def _cancel_active_locked(self, reason: str) -> None:
        if self._active is not None:
            try:
                self._active.timer.cancel()
            except Exception:
                pass
            try:
                self.board.set_zone(self._active.zone, False)
            except Exception:
                self.board.close()
            self._last_stop_reason = reason
            self._active = None

    def _timer_stop(self, zone: int, reason: str) -> None:
        with self._lock:
            if self._active and self._active.zone == zone:
                try:
                    self.board.set_zone(zone, False)
                except Exception:
                    self._last_stop_reason = f"timer_stop_error:{reason}"
                else:
                    self._last_stop_reason = reason
                self._active = None

    def stop_zone(self, zone: int | None = None, reason: str = "manual_stop") -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                try:
                    self.board.all_off()
                except Exception as exc:
                    return {"ok": False, "error": f"hardware backend failed to stop: {exc}"}
                self._last_stop_reason = reason
                return {"ok": True, "stopped": False, "reason": reason}
            if zone is not None and self._active.zone != zone:
                return {"ok": False, "error": f"zone {zone} is not active"}
            active_zone = self._active.zone
            try:
                self._cancel_active_locked(reason)
            except Exception as exc:
                return {"ok": False, "error": f"hardware backend failed to stop zone {active_zone}: {exc}"}
            return {"ok": True, "stopped": True, "zone": active_zone, "reason": reason}

    def stop_all(self, reason: str = "stop_all") -> dict[str, Any]:
        with self._lock:
            try:
                self._cancel_active_locked(reason)
                self.board.all_off()
            except Exception as exc:
                return {"ok": False, "error": f"hardware backend failed during stop_all: {exc}"}
            self._last_stop_reason = reason
            return {"ok": True, "reason": reason}

    def hardware_status(self) -> dict[str, Any]:
        try:
            return self.board.diagnostics()
        except Exception as exc:
            return {"backend": self.board.backend_name(), "ok": False, "error": str(exc)}

    def status(self) -> dict[str, Any]:
        with self._lock:
            payload = {
                "watering": self._active is not None,
                "active_zone": self._active.zone if self._active else None,
                "started_at": self._epoch_to_iso(self._active.started_at if self._active else None),
                "ends_at": self._epoch_to_iso(self._active.ends_at if self._active else None),
                "ends_at_epoch": self._active.ends_at if self._active else None,
                "requested_minutes": self._active.requested_minutes if self._active else None,
                "reason": self._active.reason if self._active else self._last_stop_reason,
                "zones": self.board.snapshot(),
                "backend": self.board.backend_name(),
            }
            return payload
