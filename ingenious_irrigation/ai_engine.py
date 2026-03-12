from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .vision import HealthAssessment
from .sensors import Telemetry


@dataclass
class ZoneDecision:
    zone: int
    base_minutes: int
    adjusted_minutes: int
    score: float
    advisory: str
    reasons: list[str]
    should_skip: bool
    delta_minutes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "zone": self.zone,
            "base_minutes": self.base_minutes,
            "adjusted_minutes": self.adjusted_minutes,
            "score": self.score,
            "advisory": self.advisory,
            "reasons": self.reasons,
            "should_skip": self.should_skip,
            "delta_minutes": self.delta_minutes,
        }


class DecisionEngine:
    """Sensor + vision fusion.

    The 0..10 score is inverted just like the better hydration logic in the uploaded repos:
      0 = very dry (needs more water)
      5 = about right
      10 = oversaturated (skip)
    """

    def score(self, telemetry: Telemetry, health: HealthAssessment) -> tuple[float, list[str]]:
        score = 5.0
        reasons: list[str] = []

        if telemetry.soil_moisture_pct is not None:
            sm = max(0.0, min(100.0, telemetry.soil_moisture_pct))
            if sm < 20:
                score -= 3.0
                reasons.append("very low soil moisture")
            elif sm < 30:
                score -= 1.5
                reasons.append("below target soil moisture")
            elif sm > 70:
                score += 3.0
                reasons.append("very high soil moisture")
            elif sm > 55:
                score += 1.5
                reasons.append("above target soil moisture")

        if telemetry.temperature_f is not None:
            if telemetry.temperature_f >= 95:
                score -= 1.0
                reasons.append("high heat increases evaporation")
            elif telemetry.temperature_f <= 45:
                score += 1.0
                reasons.append("cool weather reduces water demand")

        if telemetry.humidity is not None:
            if telemetry.humidity >= 85:
                score += 0.5
                reasons.append("high humidity reduces evaporation")
            elif telemetry.humidity <= 30:
                score -= 0.5
                reasons.append("very low humidity increases stress")

        score += (health.greenness_score - 0.5) * 2.0
        if health.dry_flag:
            score -= 1.0
            reasons.append("dry patches detected by camera")
        if health.yellow_flag:
            score -= 0.5
            reasons.append("yellowing detected")
        if health.water_flag:
            score += 2.0
            reasons.append("standing water detected")

        score = max(0.0, min(10.0, score))
        return score, reasons

    def recommend(self, zone: int, base_minutes: int, telemetry: Telemetry, health: HealthAssessment) -> ZoneDecision:
        score, reasons = self.score(telemetry, health)
        multiplier = 1.0
        advisory = "Run normal schedule."
        should_skip = False

        if score <= 2.5:
            multiplier = 1.40
            advisory = "Very dry: boost runtime today."
        elif score <= 4.0:
            multiplier = 1.20
            advisory = "Slightly dry: add a little more runtime."
        elif score <= 6.0:
            multiplier = 1.00
            advisory = "Optimal moisture: stay on schedule."
        elif score <= 8.0:
            multiplier = 0.75
            advisory = "Moist: trim runtime a bit."
        else:
            multiplier = 0.0
            should_skip = True
            advisory = "Oversaturated: skip watering."

        if health.water_flag:
            multiplier = 0.0
            should_skip = True
            advisory = "Standing water detected: skip and inspect for leaks or drainage issues."

        adjusted = int(round(max(0.0, base_minutes * multiplier)))
        return ZoneDecision(
            zone=zone,
            base_minutes=base_minutes,
            adjusted_minutes=adjusted,
            score=round(score, 2),
            advisory=advisory,
            reasons=reasons,
            should_skip=should_skip,
            delta_minutes=int(adjusted - base_minutes),
        )
