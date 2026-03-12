Astra Neon Upgrade
==================

What changed
------------
- Added a more premium neon chrome-green Astra station with a stronger 3D hologram look.
- Added animated arms, torso sway, visor sweep, and lip movement tied to Astra's listening/speaking states.
- Tuned laptop voice to prefer a smoother female browser voice when local Pi voice is off.
- Tuned offline voice to prefer a female espeak/pyttsx3 voice hint by default.
- Reduced x86 laptop warnings by skipping Raspberry Pi-only GPIO/sensor driver setup in simulation mode.

Laptop testing
--------------
- Use: `python start_laptop_dev.py`
- If you already have a `.env` file from Pi mode, laptop mode still works because `start_laptop_dev.py` forces `.env.laptop_dev`.

Pi mode
-------
- Use: `./scripts/run_offline_station.sh`
- HDMI output remains the default target in the offline profile.
