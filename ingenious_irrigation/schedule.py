from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, List

from . import config
from .utils import read_json, write_json

_ALLOWED_FREQUENCIES = {"daily", "every_x_days", "days_of_week"}


@dataclass
class ZoneSchedule:
    zone: int
    minutes: int = 10
    enabled: bool = True
    astra_control_enabled: bool = True
    start_time: str = "05:00"
    frequency: str = "daily"
    every_x_days: int = 2
    days_of_week: List[int] | None = None
    last_run_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["minutes"] = max(0, int(self.minutes))
        payload["frequency"] = self.frequency if self.frequency in _ALLOWED_FREQUENCIES else "daily"
        if not payload.get("days_of_week"):
            payload["days_of_week"] = []
        return payload


class ScheduleStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._data = self._load()

    def _default(self) -> dict[str, Any]:
        return {
            "zones": {
                str(zone): ZoneSchedule(zone=zone).to_dict() for zone in config.ZONE_IDS
            }
        }

    def _normalize_time(self, value: str | None) -> str:
        value = (value or "05:00").strip().lower().replace(" ", "")
        # Support 5, 5am, 5:30am, 17:30
        suffix = None
        if value.endswith("am") or value.endswith("pm"):
            suffix = value[-2:]
            value = value[:-2]
        if ":" in value:
            hh_s, mm_s = value.split(":", 1)
        else:
            hh_s, mm_s = value, "00"
        try:
            hour = int(hh_s)
            minute = int(mm_s)
        except Exception:
            return "05:00"
        if suffix == "pm" and hour < 12:
            hour += 12
        elif suffix == "am" and hour == 12:
            hour = 0
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return "05:00"
        return f"{hour:02d}:{minute:02d}"

    def _normalize_zone(self, zone: int, raw: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = raw or {}
        try:
            minutes = max(0, int(raw.get("minutes", 10)))
        except Exception:
            minutes = 10
        frequency = str(raw.get("frequency", "daily")).strip().lower()
        if frequency not in _ALLOWED_FREQUENCIES:
            frequency = "daily"
        try:
            every_x_days = max(1, int(raw.get("every_x_days", 2)))
        except Exception:
            every_x_days = 2
        days_of_week = raw.get("days_of_week") or []
        days_of_week = [int(x) for x in days_of_week if str(x).isdigit() and 0 <= int(x) <= 6]
        last_run_date = raw.get("last_run_date") or None
        return ZoneSchedule(
            zone=zone,
            minutes=minutes,
            enabled=bool(raw.get("enabled", True)),
            astra_control_enabled=bool(raw.get("astra_control_enabled", True)),
            start_time=self._normalize_time(str(raw.get("start_time", "05:00"))),
            frequency=frequency,
            every_x_days=every_x_days,
            days_of_week=days_of_week,
            last_run_date=last_run_date,
        ).to_dict()

    def _load(self) -> dict[str, Any]:
        raw = read_json(config.SCHEDULE_FILE, self._default())
        if not isinstance(raw, dict):
            raw = self._default()
        zones = raw.get("zones") if isinstance(raw.get("zones"), dict) else {}
        normalized = {str(zone): self._normalize_zone(zone, zones.get(str(zone), {})) for zone in config.ZONE_IDS}
        payload = {"zones": normalized}
        write_json(config.SCHEDULE_FILE, payload)
        return payload

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._load()

    def get_zone(self, zone: int) -> dict[str, Any]:
        with self._lock:
            data = self._load()
            return data["zones"][str(zone)]

    def update_zone(self, zone: int, **updates: Any) -> dict[str, Any]:
        with self._lock:
            data = self._load()
            current = data["zones"].get(str(zone), self._normalize_zone(zone, {}))
            merged = dict(current)
            merged.update({k: v for k, v in updates.items() if v is not None})
            data["zones"][str(zone)] = self._normalize_zone(zone, merged)
            write_json(config.SCHEDULE_FILE, data)
            self._data = data
            return data["zones"][str(zone)]

    def mark_ran(self, zone: int, when: datetime | None = None) -> None:
        when = when or datetime.now()
        self.update_zone(zone, last_run_date=when.date().isoformat())

    def due_zones(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now()
        current_hhmm = now.strftime("%H:%M")
        out: list[dict[str, Any]] = []
        with self._lock:
            data = self._load()
            for zone_s, item in data["zones"].items():
                if not item.get("enabled", True):
                    continue
                if item.get("start_time") != current_hhmm:
                    continue
                last_run = item.get("last_run_date")
                freq = item.get("frequency", "daily")
                if freq == "daily":
                    if last_run == now.date().isoformat():
                        continue
                elif freq == "every_x_days":
                    if last_run:
                        try:
                            last_date = datetime.fromisoformat(last_run).date()
                            if (now.date() - last_date).days < int(item.get("every_x_days", 2)):
                                continue
                        except Exception:
                            pass
                elif freq == "days_of_week":
                    if now.weekday() not in set(item.get("days_of_week") or []):
                        continue
                    if last_run == now.date().isoformat():
                        continue
                out.append({"zone": int(zone_s), **item})
        return out
