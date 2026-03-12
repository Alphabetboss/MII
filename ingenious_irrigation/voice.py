from __future__ import annotations

import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

import requests

from . import config
from .utils import iso_utc

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None


class OfflineVoiceService:
    def __init__(self) -> None:
        self._speak_lock = threading.RLock()
        self._last: dict[str, Any] = {
            'spoken_at': None,
            'text': '',
            'context': 'idle',
        }
        self._pyttsx3 = None
        self._selected_voice_id: str | None = None
        self._selected_voice_label: str | None = None
        self._voice_hint = (config.ASTRA_VOICE_NAME or 'female').strip() or 'female'
        self.engine_name = self._detect_engine()
        self.remote_audio_dir = config.STATIC_DIR / 'generated_tts'
        self.remote_audio_dir.mkdir(parents=True, exist_ok=True)

    def _detect_engine(self) -> str:
        requested = str(config.ASTRA_LOCAL_VOICE_ENGINE or 'auto').strip().lower()
        if requested in {'off', 'none', 'disabled'}:
            return 'none'
        if requested in {'elevenlabs', 'eleven', 'cloud'}:
            return 'elevenlabs' if config.ELEVENLABS_API_KEY else 'none'

        candidates = []
        if requested in {'auto', ''}:
            candidates = ['elevenlabs', 'espeak-ng', 'espeak', 'pyttsx3']
        else:
            candidates = [requested]

        for candidate in candidates:
            if candidate == 'elevenlabs' and config.ELEVENLABS_API_KEY:
                return 'elevenlabs'
            if candidate in {'espeak-ng', 'espeak'} and shutil.which(candidate):
                return candidate
            if candidate == 'pyttsx3' and pyttsx3 is not None:
                return 'pyttsx3'
        return 'none'

    def available(self) -> bool:
        return bool(config.ASTRA_LOCAL_VOICE_ENABLED) and self.engine_name != 'none'

    def _preferred_voice_label(self) -> str:
        if self.engine_name == 'elevenlabs':
            return config.ELEVENLABS_VOICE_ID
        if self.engine_name in {'espeak-ng', 'espeak'}:
            return self._espeak_voice_name()
        if self._selected_voice_label:
            return self._selected_voice_label
        return self._voice_hint

    def status(self) -> dict[str, Any]:
        return {
            'enabled': bool(config.ASTRA_LOCAL_VOICE_ENABLED),
            'engine': self.engine_name,
            'available': self.available(),
            'wake_phrase': config.ASTRA_WAKE_WORD,
            'catch_phrase': config.ASTRA_CATCH_PHRASE,
            'preferred_voice': self._preferred_voice_label(),
            'provider': self.engine_name,
            'last': dict(self._last),
            'mode': 'local_offline',
            'browser_tts_allowed': bool(config.ASTRA_ALLOW_BROWSER_TTS),
            'output_target': config.ASTRA_AUDIO_OUTPUT,
        }

    def _sanitize(self, text: str) -> str:
        cleaned = re.sub(r'\s+', ' ', str(text or '').strip())
        return cleaned[:320]

    def _espeak_voice_name(self) -> str:
        hint = self._voice_hint.lower()
        if hint in {'', 'auto', 'default'}:
            return 'en-us+f3'
        if hint in {'female', 'woman', 'lady', 'astra'}:
            return 'en-us+f3'
        return self._voice_hint

    def _pyttsx3_voice_keywords(self) -> list[str]:
        hint = self._voice_hint.lower()
        if hint in {'', 'auto', 'default', 'female', 'woman', 'lady', 'astra'}:
            return [
                'aria', 'zira', 'jenny', 'samantha', 'ava', 'serena', 'hazel', 'susan',
                'female', 'woman', 'english-us', 'english_us', 'english',
            ]
        terms = [item.strip().lower() for item in re.split(r'[,/]+', hint) if item.strip()]
        return terms or ['english']

    def _ensure_pyttsx3_voice(self) -> None:
        if pyttsx3 is None:
            return
        if self._pyttsx3 is None:
            self._pyttsx3 = pyttsx3.init()
            self._pyttsx3.setProperty('rate', int(config.ASTRA_VOICE_RATE_WPM))

        if self._selected_voice_id is not None:
            try:
                self._pyttsx3.setProperty('voice', self._selected_voice_id)
            except Exception:
                pass
            return

        voices = []
        try:
            voices = list(self._pyttsx3.getProperty('voices') or [])
        except Exception:
            voices = []
        if not voices:
            return

        def voice_blob(item: Any) -> str:
            parts = [
                str(getattr(item, 'id', '') or ''),
                str(getattr(item, 'name', '') or ''),
                ' '.join(str(v) for v in (getattr(item, 'languages', []) or [])),
                str(getattr(item, 'gender', '') or ''),
            ]
            return ' '.join(parts).lower()

        selected = None
        keywords = self._pyttsx3_voice_keywords()
        for keyword in keywords:
            for voice in voices:
                if keyword in voice_blob(voice):
                    selected = voice
                    break
            if selected is not None:
                break
        if selected is None:
            selected = voices[0]

        self._selected_voice_id = str(getattr(selected, 'id', '') or '') or None
        self._selected_voice_label = str(getattr(selected, 'name', '') or self._voice_hint)
        if self._selected_voice_id:
            try:
                self._pyttsx3.setProperty('voice', self._selected_voice_id)
            except Exception:
                pass

def _safe_audio_name(self, context: str) -> Path:
    stamp = iso_utc().replace(':', '').replace('-', '').replace('T', '_').replace('Z', '')
    return self.remote_audio_dir / f"astra_{context}_{stamp}.mp3"

def _speak_via_elevenlabs(self, text: str, context: str) -> dict[str, Any]:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        'xi-api-key': config.ELEVENLABS_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg',
    }
    payload = {
        'text': text,
        'model_id': config.ELEVENLABS_MODEL_ID,
        'output_format': config.ELEVENLABS_OUTPUT_FORMAT,
        'voice_settings': {
            'stability': 0.48,
            'similarity_boost': 0.82,
            'style': 0.32,
            'use_speaker_boost': True,
        },
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    out_path = self._safe_audio_name(context)
    out_path.write_bytes(resp.content)
    return {
        'ok': True,
        'engine': 'elevenlabs',
        'audio_url': f"/static/generated_tts/{out_path.name}",
        'context': context,
        **self.status(),
    }

    def estimate_seconds(self, text: str) -> float:
        words = max(1, len(self._sanitize(text).split()))
        wpm = max(110, min(280, int(config.ASTRA_VOICE_RATE_WPM)))
        seconds = (words / float(wpm)) * 60.0 + 0.9
        return round(max(1.4, min(12.0, seconds)), 2)

    def speak(self, text: str, context: str = 'general') -> dict[str, Any]:
        line = self._sanitize(text)
        if not line:
            return {'ok': False, 'error': 'No text to speak.', **self.status()}
        if not config.ASTRA_LOCAL_VOICE_ENABLED:
            return {'ok': False, 'error': 'Local Astra voice is disabled.', **self.status()}
        if self.engine_name == 'none':
            return {
                'ok': False,
                'error': 'No offline voice engine found. Install espeak-ng or pyttsx3.',
                **self.status(),
            }

        payload = {
            'spoken_at': iso_utc(),
            'text': line,
            'context': context,
        }
        self._last = dict(payload)

        if self.engine_name == 'elevenlabs':
            try:
                result = self._speak_via_elevenlabs(line, context)
                result['estimated_seconds'] = self.estimate_seconds(line)
                return result
            except Exception as exc:
                return {'ok': False, 'error': f'ElevenLabs request failed: {exc}', **self.status()}

        worker = threading.Thread(target=self._speak_blocking, args=(line,), daemon=True)
        worker.start()
        return {
            'ok': True,
            'engine': self.engine_name,
            'estimated_seconds': self.estimate_seconds(line),
            'context': context,
            **self.status(),
        }


    def _speak_blocking(self, text: str) -> None:
        with self._speak_lock:
            if self.engine_name in {'espeak-ng', 'espeak'}:
                cmd = [
                    self.engine_name,
                    '-s', str(int(config.ASTRA_VOICE_RATE_WPM)),
                    '-p', str(int(config.ASTRA_VOICE_PITCH)),
                    '-v', self._espeak_voice_name(),
                    text,
                ]
                try:
                    subprocess.run(
                        cmd,
                        check=False,
                        timeout=max(6.0, self.estimate_seconds(text) * 2.5),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    return
                return

            if self.engine_name == 'pyttsx3' and pyttsx3 is not None:
                try:
                    self._ensure_pyttsx3_voice()
                    if self._pyttsx3 is None:
                        return
                    self._pyttsx3.say(text)
                    self._pyttsx3.runAndWait()
                except Exception:
                    return


_VOICE: OfflineVoiceService | None = None


def get_voice_service() -> OfflineVoiceService:
    global _VOICE
    if _VOICE is None:
        _VOICE = OfflineVoiceService()
    return _VOICE
