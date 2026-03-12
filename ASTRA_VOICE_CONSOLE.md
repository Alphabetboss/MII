# Astra Voice Console Notes

This build adds a floating Astra voice window to the dashboard.

## Included
- Animated Astra avatar window
- Drag-to-move console on desktop widths
- Text chat tied to the real Flask backend
- Browser text-to-speech for spoken replies
- Optional browser speech-to-text for microphone input
- Status-aware replies using live telemetry / schedule / simulation data

## Browser notes
- Text-to-speech uses the browser's built-in speech engine.
- Voice input uses the browser's Web Speech recognition API when available.
- If voice input is unavailable, text chat still works normally.

## Future upgrades
- Add phoneme-based lip sync
- Add custom TTS voice model running locally on the Pi
- Add wake-word support (e.g., "Hey Astra")
- Add camera-triggered facial expression changes


Laptop test quick start
-----------------------
- Linux/macOS: `./scripts/run_laptop_dev.sh`
- Cross-platform: `python start_laptop_dev.py`
- Open `http://127.0.0.1:5051` and use the simulation dashboard.
- Laptop mode uses browser speech by default so you can test Astra immediately.
