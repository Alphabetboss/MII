Astra HDMI and laptop test notes
================================

Pi HDMI mode
------------
- `.env.offline` now sets `II_ASTRA_AUDIO_OUTPUT=HDMI`.
- `./scripts/run_offline_station.sh` sources `.env`, then runs `./scripts/configure_audio_output.sh` before starting Flask.
- The audio helper tries PipeWire (`wpctl`), PulseAudio (`pactl`), then ALSA (`amixer`) in a best-effort order.

Laptop mode
-----------
- `./scripts/run_laptop_dev.sh` starts the app in safe simulation mode with browser voice enabled.
- `python start_laptop_dev.py` is included as a cross-platform launcher.
- Laptop mode keeps the valve, camera, and field I/O simulated.
