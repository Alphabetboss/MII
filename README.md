# Ingenious Irrigation - Astra Premium Offline Station

This package is a simulation-first control stack for your Raspberry Pi 5 with a dedicated Astra station.

What is new:
- Docked Astra Station panel with your 3D avatar
- Local Pi-first offline speech output (espeak-ng, espeak, or pyttsx3)
- Branded Astra personality: futuristic, witty, confident, pro technician
- Wake phrase parsing for typed commands: start commands with "Astra"
- Premium startup, safety, and diagnostic response lines
- Safe simulation mode for relay, sensors, and camera while you are still prototyping

## Quick start (offline simulation)
1. Run `./install_pi.sh`
2. Start with `./scripts/run_offline_station.sh`
3. Open `http://<your-pi-ip>:5051`
4. Type commands like `Astra, give me a quick system summary`

## Offline voice notes
- Best local voice path on Raspberry Pi OS: `espeak-ng`
- Browser speech is intentionally disabled by default in the offline profile
- Add a USB microphone later when you want true always-listening wake-word voice input on the Pi

## Real hardware later
When you are ready to connect the ESP32, valve, and camera:
- disable the simulation flags in `.env`
- set `II_HARDWARE_BACKEND=ESP32_SERIAL`
- set `II_SENSOR_BACKEND=ESP32`
- confirm the real USB serial path on the Pi
- replace the synthetic camera with your real camera source

## Files worth opening first
- `.env.offline`
- `ASTRA_BRAND_PROFILE.md`
- `FUTURE_HARDWARE_BOOKMARKS.md`
- `WHAT_I_NEED_FROM_YOU.md`


Laptop test quick start
-----------------------
- Linux/macOS: `./scripts/run_laptop_dev.sh`
- Cross-platform: `python start_laptop_dev.py`
- Open `http://127.0.0.1:5051` and use the simulation dashboard.
- Laptop mode uses browser speech by default so you can test Astra immediately.


## New in this merged build
- Camera-based water detection / leak guard integrated into autonomy.
- Astra AI master toggle and Water Detection toggle in AI settings.
- Optional ElevenLabs voice output using environment variables:
  - `II_ASTRA_TTS_PROVIDER=ELEVENLABS`
  - `II_ELEVENLABS_API_KEY=...`
  - `II_ELEVENLABS_VOICE_ID=Rachel`
- If ElevenLabs is enabled, `/api/astra/speak` returns an `audio_url` that browsers can play directly.
