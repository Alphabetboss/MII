from __future__ import annotations

import re
import random
from typing import Any

from . import config
from .controller import IrrigationController
from .schedule import ScheduleStore
from .service import AutonomousService
from .simulation import get_simulation_profile


class AstraAssistant:
    def __init__(self, controller: IrrigationController, schedule_store: ScheduleStore, service: AutonomousService) -> None:
        self.controller = controller
        self.schedule_store = schedule_store
        self.service = service
        self.simulation = get_simulation_profile()

    def _zone_from_text(self, text: str, default: int = 1) -> int:
        match = re.search(r'zone\s*(\d+)', text)
        return int(match.group(1)) if match else default

    def _strip_wake_phrase(self, text: str) -> str:
        line = (text or '').strip()
        if not line:
            return ''
        wake = re.escape(config.ASTRA_WAKE_WORD.lower())
        patterns = [
            rf'^(?:hey\s+|ok\s+)?{wake}[,!?\s:-]*',
            rf'^(?:hey\s+|okay\s+)?{wake}[,!?\s:-]*',
        ]
        lowered = line.lower()
        for pattern in patterns:
            lowered = re.sub(pattern, '', lowered, count=1).strip()
        return lowered or line.lower()

    def _schedule_summary(self) -> str:
        data = self.schedule_store.snapshot()
        parts = []
        for zone, cfg in sorted(data.get('zones', {}).items(), key=lambda item: int(item[0])):
            freq = str(cfg.get('frequency', 'daily')).replace('_', ' ')
            parts.append(f"Zone {zone}: {cfg.get('start_time')} for {cfg.get('minutes')} min ({freq})")
        if not parts:
            return 'No zones are configured yet. Clean slate, ready for layout.'
        return ' | '.join(parts)

    def _analysis(self, zone: int | None = None, force: bool = False) -> dict[str, Any]:
        latest = self.service.latest_telemetry() or {}
        if force or not latest.get('telemetry'):
            return self.service.analyze_once(zone=zone)
        if zone is not None and latest.get('decision') is None:
            return self.service.analyze_once(zone=zone)
        return latest

    def _metric_line(self, analysis: dict[str, Any]) -> str:
        telemetry = analysis.get('telemetry') or {}
        parts = []
        humidity = telemetry.get('humidity')
        if humidity is not None:
            parts.append(f"humidity {float(humidity):.1f}%")
        temp_c = telemetry.get('temperature_c')
        if temp_c is not None:
            parts.append(f"temperature {float(temp_c):.1f} C")
        soil = telemetry.get('soil_moisture_pct')
        if soil is not None:
            parts.append(f"soil {float(soil):.1f}%")
        pressure = telemetry.get('pressure_psi')
        if pressure is not None:
            parts.append(f"pressure {float(pressure):.1f} PSI")
        if not parts:
            return 'Telemetry is not available yet. The yard is still off the record.'
        return ', '.join(parts)

    def _scenario_hint(self, analysis: dict[str, Any]) -> str:
        if not self.simulation.active():
            return ''
        profile = self.simulation.snapshot()
        label = profile.get('scenario_label', 'Simulation')
        if profile.get('people_present'):
            return f'Simulation profile {label} is active, with a person in the spray path.'
        return f'Simulation profile {label} is active.'

    def _current_summary(self, zone: int = 1, force: bool = False) -> str:
        analysis = self._analysis(zone=zone, force=force)
        controller = self.controller.status()
        health = analysis.get('health') or {}
        people = analysis.get('people') or {}
        decision = analysis.get('decision') or {}
        if controller.get('watering'):
            state_text = f'Zone {controller.get("active_zone")} is live right now.'
        else:
            state_text = 'All zones are idle and standing by.'
        lines = [
            f'{config.ASTRA_NAME} here. {state_text}',
            self._metric_line(analysis),
        ]
        if health.get('summary'):
            lines.append(f"Visual reads {health['summary']}")
        if decision.get('advisory'):
            lines.append(f"My call: {decision['advisory']}")
        if people.get('people_present'):
            lines.append(f"Safety lock engaged. {people.get('count', 1)} person detected in the spray area.")
        hint = self._scenario_hint(analysis)
        if hint:
            lines.append(hint)
        return ' '.join(str(part).strip() for part in lines if str(part).strip())

    def _zone_start_line(self, zone: int, minutes: int) -> str:
        return (
            f'On it. Zone {zone} is running for {minutes} minutes. '
            'Clean coverage, no drama — and I’m watching pressure and timing the whole way.'
        )

    def _zone_stop_line(self) -> str:
        return 'Water is off. Lines are safe, zones are idle, and I’m ready for your next move.'

    def _safety_line(self, people_count: int) -> str:
        noun = 'person' if people_count == 1 else 'people'
        return (
            f'Safety lock engaged. I see {people_count} {noun} in the spray path — '
            'so watering stays paused until the area clears. Dry shoes are a feature.'
        )

    def _health_line(self, zone: int, analysis: dict[str, Any]) -> str:
        """
        Construct a conversational response summarizing the current health assessment
        and watering recommendation for a given zone.

        The response includes:
          • a human‑friendly summary of the visual assessment (e.g., healthy turf, dry patches)
          • an optional remedy if corrective action is needed
          • a hydration score (0‑10 scale) when available
          • the recommendation or advisory from the decision engine
          • underlying reasons from the decision engine to lend context

        This richer output helps Astra explain what she sees and why she
        recommends certain actions, addressing feedback that her answers lacked detail.
        """
        health: dict[str, Any] = analysis.get('health') or {}
        decision: dict[str, Any] = analysis.get('decision') or {}

        # Visual summary and remedy from vision engine
        summary: str = health.get('summary', 'Camera feedback is limited right now.')
        remedy: str = health.get('remedy', '')

        # Decision engine outputs
        score = decision.get('score')
        advisory: str = decision.get('advisory', '')
        reasons: list[str] = decision.get('reasons', [])  # underlying factors influencing the score

        # Build parts of the reply
        parts: list[str] = [f'Zone {zone} visual check complete.', summary]
        if remedy:
            parts.append(f'Remedy: {remedy}')
        if score is not None:
            parts.append(f'Hydration score {score}/10.')
        if advisory:
            parts.append(advisory)
        if reasons:
            # Combine reasons into a single parenthetical phrase
            reasons_text = ', '.join(reasons)
            parts.append(f'Reasons: {reasons_text}.')

        # Join the pieces with spaces and ensure extra whitespace is trimmed
        reply = ' '.join(part.strip() for part in parts if part).strip()
        return reply

    def briefing(self) -> dict[str, Any]:
        reply = (
            f'{config.ASTRA_CATCH_PHRASE} '
            f'{self._current_summary(zone=1, force=False)} '
            f'Say {config.ASTRA_WAKE_WORD}, then tell me what you need.'
        )
        return {
            'reply': reply,
            'suggestions': [
                'Astra, give me a quick system summary',
                'Astra, analyze zone 1',
                'Astra, run zone 1 for 5 minutes',
                'Astra, simulate dry',
                'Astra, stop all watering',
            ],
            'wake_phrase': config.ASTRA_WAKE_WORD,
            'catch_phrase': config.ASTRA_CATCH_PHRASE,
            'personality': config.ASTRA_PERSONALITY,
        }

    def profile(self) -> dict[str, Any]:
        return {
            'name': config.ASTRA_NAME,
            'wake_phrase': config.ASTRA_WAKE_WORD,
            'catch_phrase': config.ASTRA_CATCH_PHRASE,
            'personality': config.ASTRA_PERSONALITY,
            'station_style': config.ASTRA_STATION_STYLE,
            'wake_ack_lines': [
                "I'm listening.",
                'Go ahead.',
                'What do you need?',
                'Yep — talk to me.',
            ],
            'startup_lines': [
                config.ASTRA_CATCH_PHRASE,
                f"{config.ASTRA_NAME} here. I’m your calm, sharp set of eyes on pressure, coverage, and plant health.",
                'Precision watering. Professional timing. No wasted water — because we’re not paying to soak sidewalks.',
            ],
            'safety_lines': [
                'Safety lock engaged. No one gets soaked on my watch.',
                'Pressure anomaly detected. I’d rather pause than turn your yard into a slip-n-slide.',
            ],
            'diagnostic_lines': [
                'Your turf is talking. I catch moisture stress before it becomes dead spots.',
                'I tune runtime from data, not vibes.',
            ],
        }

    def respond(self, text: str) -> str:
        raw = (text or '').strip()
        msg = self._strip_wake_phrase(raw)
        if not msg:
            # If the user only said the wake phrase ("Astra"), acknowledge instead of dumping a status report.
            wake = (config.ASTRA_WAKE_WORD or 'astra').strip().lower()
            lowered = raw.lower()
            if wake and (lowered == wake or lowered in {f'hey {wake}', f'ok {wake}', f'okay {wake}', f'hey, {wake}', f'ok, {wake}', f'okay, {wake}'}):
                return random.choice([
                    "I'm listening.",
                    'Go ahead.',
                    'What do you need?',
                    'Yep — talk to me.',
                ])
            return self._current_summary(zone=1, force=False)

        lower = msg.lower()

        if any(phrase in lower for phrase in ['brief', 'summary', 'report', 'system overview', 'quick status']):
            return self._current_summary(zone=self._zone_from_text(lower), force=False)

        if 'simulate' in lower or 'scenario' in lower:
            for scenario in ('healthy', 'dry', 'yellow', 'water'):
                if scenario in lower:
                    self.simulation.update(scenario=scenario)
                    self.service.analyze_once(zone=1)
                    labels = {
                        'healthy': 'Balanced turf. Efficient demand.',
                        'dry': 'High demand. Expect longer runtime recommendations.',
                        'yellow': 'Stress is showing. Coverage tuning advised.',
                        'water': 'Overwatering conditions. Leak or drainage check advised.',
                    }
                    return f'Simulation switched to {scenario}. {labels.get(scenario, "Profile updated.")}'
            if 'person' in lower:
                person_on = not any(term in lower for term in ('off', 'clear', 'remove', 'gone', 'false', '0'))
                self.simulation.update(people_present=person_on)
                self.service.analyze_once(zone=1)
                return self._safety_line(1) if person_on else 'Spray path is clear again. Safety hold released.'

        m = re.search(r'(?:start|run|water)\s+zone\s*(\d+)\s*(?:for\s*(\d+)\s*(?:minutes?|mins?))?', lower)
        if m:
            zone = int(m.group(1))
            zone_cfg = self.schedule_store.snapshot().get('zones', {}).get(str(zone), {'minutes': 10})
            minutes = int(m.group(2) or zone_cfg.get('minutes', 10))
            result = self.controller.start_zone(zone, minutes, reason='astra_command')
            if result.get('ok'):
                return self._zone_start_line(zone, minutes)
            return f"I cannot start zone {zone} yet: {result.get('error', 'unknown error')}."

        m = re.search(r'set\s+zone\s*(\d+)\s*(?:to|for)?\s*(\d+)\s*(?:minutes?|mins?)', lower)
        if m:
            zone = int(m.group(1))
            minutes = int(m.group(2))
            self.schedule_store.update_zone(zone, minutes=minutes)
            return f'Locked in. Zone {zone} is now configured for {minutes} minutes.'

        m = re.search(r'(?:stop|shut off|cancel).*(?:zone\s*(\d+))?', lower)
        if m and any(word in lower for word in ['stop', 'shut off', 'cancel']):
            zone = int(m.group(1)) if m.group(1) else None
            result = self.controller.stop_zone(zone=zone, reason='astra_stop')
            if result.get('ok'):
                return self._zone_stop_line()
            return f"I could not stop that zone: {result.get('error', 'unknown error')}."

        if 'schedule' in lower or 'timer' in lower:
            return f'Current timing matrix: {self._schedule_summary()}'

        if 'status' in lower or "what's running" in lower or 'whats running' in lower:
            controller = self.controller.status()
            if controller.get('watering'):
                return f'Zone {controller["active_zone"]} is active right now. Runtime is in progress.'
            return 'No zone is running right now. The manifold is quiet.'

        if any(key in lower for key in ['humidity', 'temperature', 'soil', 'pressure', 'sensor']):
            analysis = self._analysis(zone=self._zone_from_text(lower), force=False)
            return f'Sensor sweep complete: {self._metric_line(analysis)}'

        if any(key in lower for key in ['health', 'analyze', 'camera', 'grass', 'plants', 'what do you see', 'what are you seeing']):
            zone = self._zone_from_text(lower)
            analysis = self.service.analyze_once(zone=zone)
            return self._health_line(zone, analysis)

        if any(key in lower for key in ['recommend', 'advice', 'what should i do', 'watering recommendation']):
            zone = self._zone_from_text(lower)
            analysis = self.service.analyze_once(zone=zone)
            decision = analysis.get('decision') or {}
            if decision.get('advisory'):
                return f'My recommendation for zone {zone}: {decision["advisory"]}'
            return 'I need a fresh analysis before I can make a clean recommendation.'

        if any(key in lower for key in ['person', 'people', 'someone got wet', 'someone walks', 'safety']):
            analysis = self.service.analyze_once(zone=self._zone_from_text(lower))
            people = analysis.get('people') or {}
            if people.get('people_present'):
                return self._safety_line(int(people.get('count', 1) or 1))
            return 'Spray path is clear. No person detected in the latest frame.'

        if any(key in lower for key in ['hello', 'hi', 'hey']):
            return f'{config.ASTRA_CATCH_PHRASE} Give me a zone, a status request, or a health check.'

        if 'help' in lower or 'what can you do' in lower:
            return (
                'I can run or stop zones, tune runtimes, summarize schedules, analyze plant health, '
                'switch simulation scenarios, report live sensors, and keep the system safe when people '
                'or pressure conditions say stand down.'
            )

        return (
            'I stay focused on irrigation, plant health, and safety. '
            'Try: Astra, give me a quick system summary. Astra, run zone 1 for 8 minutes. '
            'Astra, simulate dry. Astra, analyze zone 1.'
        )
