from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any

from . import config
from .ai_engine import DecisionEngine
from .controller import IrrigationController
from .notifications import Notifier
from .schedule import ScheduleStore
from .sensors import SensorSuite
from .utils import append_jsonl, iso_utc, write_json, tail_jsonl
from .vision import VisionEngine


class AutonomousService:
    def __init__(
        self,
        controller: IrrigationController,
        schedule_store: ScheduleStore,
        sensors: SensorSuite,
        vision: VisionEngine,
        notifier: Notifier,
    ) -> None:
        self.controller = controller
        self.schedule_store = schedule_store
        self.sensors = sensors
        self.vision = vision
        self.notifier = notifier
        self.engine = DecisionEngine()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False
        self._last_tick: str | None = None
        self._last_analysis: dict[str, Any] | None = None

    def _load_runtime_ai_settings(self) -> dict[str, Any]:
        path = config.DATA_ROOT / "data" / "ui_settings.json"
        try:
            payload = json.loads(path.read_text()) if path.exists() else {}
            ai = payload.get("ai") if isinstance(payload, dict) else {}
            return ai if isinstance(ai, dict) else {}
        except Exception:
            return {}

    def start(self) -> None:
        if not config.AUTONOMY_ENABLED:
            return
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, name="ii-autonomy", daemon=True)
            self._thread.start()
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            self._running = False

    def _log_incident(self, kind: str, message: str, extra: dict[str, Any] | None = None, alert: bool = False) -> None:
        payload = {"ts": iso_utc(), "kind": kind, "message": message, "extra": extra or {}}
        append_jsonl(config.INCIDENT_LOG, payload)
        if alert:
            self.notifier.notify(f"Ingenious Irrigation: {kind}", message, level="warning")

    def latest_telemetry(self) -> dict[str, Any]:
        return self._last_analysis or {
            "ts": self._last_tick,
            "telemetry": None,
            "health": None,
            "water_detection": None,
            "people": None,
        }

    def recent_decisions(self, limit: int = 100) -> list[dict[str, Any]]:
        return tail_jsonl(config.DECISION_LOG, limit=limit)

    def analyze_once(self, zone: int | None = None) -> dict[str, Any]:
        frame = self.vision.capture_frame()
        people = self.vision.detect_people(frame) if frame is not None else None
        health = self.vision.analyze_health(frame)
        water_detection = self.vision.detect_water_flow(frame)
        telemetry = self.sensors.read()
        decision = None
        if zone is not None:
            zone_cfg = self.schedule_store.get_zone(zone)
            decision = self.engine.recommend(zone, int(zone_cfg.get("minutes", 10)), telemetry, health)
        payload = {
            "ts": iso_utc(),
            "telemetry": telemetry.as_dict(),
            "health": health.as_dict(),
            "water_detection": water_detection.as_dict(),
            "people": people.as_dict() if people is not None else None,
            "decision": decision.as_dict() if decision is not None else None,
        }
        self._last_analysis = payload
        write_json(config.TELEMETRY_FILE, payload)
        return payload

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                self._log_incident("service_error", f"Autonomy loop error: {exc}")
            self._stop_event.wait(config.POLL_SECONDS)

def _next_enabled_zone(self, current_zone: int) -> dict[str, Any] | None:
    zones = self.schedule_store.snapshot().get('zones', {})
    ordered = sorted(int(z) for z in zones.keys())
    if not ordered:
        return None
    if current_zone not in ordered:
        next_zone = ordered[0]
        return {'zone': next_zone, **zones.get(str(next_zone), {})}
    start_idx = ordered.index(current_zone)
    for offset in range(1, len(ordered)):
        candidate = ordered[(start_idx + offset) % len(ordered)]
        cfg = zones.get(str(candidate), {})
        if cfg.get('enabled', True):
            return {'zone': candidate, **cfg}
    return None

def _handle_water_detection(self, ai_settings: dict[str, Any], status: dict[str, Any], analysis: dict[str, Any]) -> bool:
    if not ai_settings.get('astra_enabled', True):
        return False
    if not ai_settings.get('water_detection_enabled', True):
        return False
    water = analysis.get('water_detection') or {}
    if not water.get('detected'):
        return False

    if status.get('watering') and status.get('active_zone'):
        current_zone = int(status['active_zone'])
        self.controller.stop_zone(current_zone, reason='water_flow_leak_detected')
        message = (
            f'Possible leak detected while Zone {current_zone} was running. '
            'Astra stopped that zone and moved on to protect the system.'
        )
        self._log_incident('zone_leak_detected', message, {'zone': current_zone, 'water_detection': water}, alert=True)
        self.notifier.notify('Ingenious Irrigation: Zone leak suspected', message, level='warning')
        next_zone_cfg = self._next_enabled_zone(current_zone)
        if next_zone_cfg is not None:
            next_zone = int(next_zone_cfg['zone'])
            next_minutes = max(1, int(next_zone_cfg.get('minutes', 10)))
            self.controller.start_zone(next_zone, next_minutes, reason='continue_after_zone_leak')
        return True

    self.controller.stop_all(reason='water_flow_main_leak_detected')
    main_message = (
        'Possible main water supply leak detected while no irrigation zone was running. '
        'Astra shut down watering outputs immediately.'
    )
    self._log_incident('main_supply_leak_detected', main_message, {'water_detection': water}, alert=True)
    self.notifier.notify('Ingenious Irrigation: Main leak suspected', main_message, level='warning')
    return True

    def _tick(self) -> None:
        now = datetime.now()
        self._last_tick = iso_utc()
        analysis = self.analyze_once()
        telemetry = analysis["telemetry"]
        health = analysis["health"]
        people = analysis["people"] or {"people_present": False, "count": 0, "boxes": []}

        status = self.controller.status()
        pressure = telemetry.get("pressure_psi")
        if pressure is not None and (pressure < config.PRESSURE_LOW_PSI or pressure > config.PRESSURE_HIGH_PSI):
            if status.get("watering"):
                self.controller.stop_all(reason="pressure_fault")
                self._log_incident(
                    "pressure_fault",
                    f"Pressure out of safe range ({pressure:.1f} PSI). Water shut off.",
                    {"pressure_psi": pressure},
                    alert=True,
                )
                return

        ai_settings = self._load_runtime_ai_settings()

        if (
            status.get("watering")
            and people.get("people_present")
            and ai_settings.get("people_avoidance_enabled", True)
        ):
            self.controller.stop_all(reason="person_detected")
            self._log_incident(
                "person_detected",
                f"A person entered the watering area. Water shut off to avoid spraying someone.",
                {"count": people.get("count", 0)},
                alert=False,
            )
            return

        # Only trigger scheduled runs if idle.
        if status.get("watering"):
            return

        due = self.schedule_store.due_zones(now)
        if not due:
            return

        for zone_cfg in due:
            zone = int(zone_cfg["zone"])
            if not zone_cfg.get("astra_control_enabled", True):
                result = self.controller.start_zone(zone, int(zone_cfg.get("minutes", 10)), reason="scheduled_manual_profile")
                if result.get("ok"):
                    self.schedule_store.mark_ran(zone, now)
                break

            decision = self.engine.recommend(
                zone=zone,
                base_minutes=int(zone_cfg.get("minutes", 10)),
                telemetry=self.sensors.read(),
                health=self.vision.analyze_health(self.vision.capture_frame()),
            )
            if not ai_settings.get("intelligent_override_enabled", True):
                decision.adjusted_minutes = int(zone_cfg.get("minutes", 10))
                decision.delta_minutes = 0
                decision.advisory = "Astra followed the saved schedule with no automatic changes."
            else:
                try:
                    limit_pct = max(1, int(ai_settings.get("intelligent_override_limit_pct", 12)))
                except Exception:
                    limit_pct = 12
                base_minutes = max(1, int(zone_cfg.get("minutes", 10)))
                max_delta = max(1, round(base_minutes * (limit_pct / 100.0)))
                if decision.adjusted_minutes > base_minutes + max_delta:
                    decision.adjusted_minutes = base_minutes + max_delta
                elif decision.adjusted_minutes < base_minutes - max_delta:
                    decision.adjusted_minutes = max(0, base_minutes - max_delta)
                decision.delta_minutes = int(decision.adjusted_minutes - base_minutes)
            record = {
                "ts": iso_utc(),
                "zone": zone,
                "schedule": zone_cfg,
                "decision": decision.as_dict(),
            }
            append_jsonl(config.DECISION_LOG, record)

            if decision.should_skip or decision.adjusted_minutes <= 0:
                self.schedule_store.mark_ran(zone, now)
                if "Standing water" in decision.advisory:
                    self._log_incident("skip_due_to_water", f"Zone {zone}: {decision.advisory}", {"zone": zone}, alert=False)
                continue

            result = self.controller.start_zone(zone, decision.adjusted_minutes, reason="autonomous_schedule")
            if result.get("ok"):
                self.schedule_store.mark_ran(zone, now)
                if health.get("dry_flag"):
                    self.notifier.notify(
                        f"Zone {zone} increased runtime",
                        f"Astra increased zone {zone} to {decision.adjusted_minutes} minutes because the yard looked dry.",
                        level="info",
                    )
                break

    def status(self) -> dict[str, Any]:
        return {
            "autonomy_enabled": config.AUTONOMY_ENABLED,
            "running": self._running,
            "last_tick": self._last_tick,
            "last_analysis": self._last_analysis,
        }
