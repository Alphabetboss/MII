
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from . import config
from .simulation import get_simulation_profile


@dataclass
class WaterDetectionAssessment:
    detected: bool
    motion_ratio: float
    water_ratio: float
    score: float
    summary: str
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            'detected': self.detected,
            'motion_ratio': round(self.motion_ratio, 4),
            'water_ratio': round(self.water_ratio, 4),
            'score': round(self.score, 4),
            'summary': self.summary,
            'raw': self.raw,
        }


class WaterDetectionEngine:
    def __init__(self) -> None:
        self._prev_gray: np.ndarray | None = None
        self._consecutive_hits = 0
        self._sim = get_simulation_profile()

    def detect(self, frame: np.ndarray | None) -> WaterDetectionAssessment:
        if frame is None:
            self._prev_gray = None
            self._consecutive_hits = 0
            return WaterDetectionAssessment(False, 0.0, 0.0, 0.0, 'No frame available for water detection.', {'error': 'no_frame'})

        if self._sim.active() and self._sim.snapshot().get('scenario') == 'water':
            self._consecutive_hits = max(self._consecutive_hits + 1, config.WATER_DETECTION_CONSECUTIVE)
            return WaterDetectionAssessment(True, 0.12, 0.08, 0.95, 'Simulation indicates active flowing water.', {'method': 'simulation'})

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        low_sat_bright = cv2.inRange(hsv, np.array([0, 0, 140]), np.array([180, 85, 255]))
        blue_cyan = cv2.inRange(hsv, np.array([75, 20, 60]), np.array([130, 255, 255]))
        reflective_mask = cv2.bitwise_or(low_sat_bright, blue_cyan)
        reflective_mask = cv2.morphologyEx(reflective_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        motion_ratio = 0.0
        motion_mask = np.zeros_like(gray)
        if self._prev_gray is not None:
            diff = cv2.absdiff(gray, self._prev_gray)
            _, motion_mask = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
            motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            motion_mask = cv2.dilate(motion_mask, np.ones((3, 3), np.uint8), iterations=1)
            motion_ratio = float(np.count_nonzero(motion_mask)) / float(motion_mask.size)

        self._prev_gray = gray
        combined = cv2.bitwise_and(motion_mask, reflective_mask)
        water_ratio = float(np.count_nonzero(combined)) / float(combined.size)

        motion_component = min(1.0, motion_ratio / max(config.WATER_DETECTION_MIN_MOTION_RATIO, 1e-6))
        water_component = min(1.0, water_ratio / max(config.WATER_DETECTION_MIN_WATER_RATIO, 1e-6))
        score = 0.55 * water_component + 0.45 * motion_component
        likely = (
            motion_ratio >= config.WATER_DETECTION_MIN_MOTION_RATIO and
            water_ratio >= config.WATER_DETECTION_MIN_WATER_RATIO and
            score >= config.WATER_DETECTION_SCORE_THRESHOLD
        )

        if likely:
            self._consecutive_hits += 1
        else:
            self._consecutive_hits = 0

        detected = self._consecutive_hits >= max(1, config.WATER_DETECTION_CONSECUTIVE)
        summary = 'Possible flowing water detected.' if detected else 'No convincing flowing-water pattern detected.'
        raw = {
            'method': 'motion_reflective_heuristic',
            'consecutive_hits': self._consecutive_hits,
            'threshold_hits_required': config.WATER_DETECTION_CONSECUTIVE,
        }
        return WaterDetectionAssessment(detected, motion_ratio, water_ratio, score, summary, raw)
