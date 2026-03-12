# Hardware Profile - Current Bench Setup

## Confirmed hardware
- Raspberry Pi 5 running Linux
- SparkFun ESP32 Thing Plus
- DHT11 temperature / humidity sensor
- Inland SRD-05VDC-SL-C single relay module
- S2Pi Tiny NVMe
- Touchscreen monitor attached to the Pi

## Software assumptions in this build
- Pi runs the Flask app, camera analysis, dashboard, and autonomous decision engine.
- ESP32 acts as the field controller over USB serial.
- The relay and DHT11 are attached to the ESP32.
- Current deployment is configured for 1 irrigation zone.
- Logs / telemetry can be moved to the NVMe with `II_DATA_ROOT`.

## Default firmware pin assumptions
- DHT11 data pin: GPIO 4 on ESP32
- Relay input pin: GPIO 26 on ESP32
- Relay logic: active-low

## Bench test checklist
1. Flash `firmware/esp32_field_controller/esp32_field_controller.ino` to the ESP32.
2. Connect the ESP32 to the Pi over USB.
3. Verify the serial port (`/dev/ttyACM0` or `/dev/ttyUSB0`).
4. Start the app and open `/api/field/ping`.
5. Run `POST /api/zone/1/run` for 1 minute.
6. Confirm the relay clicks cleanly.
7. Confirm DHT11 readings appear at `/api/field/sensors`.

## If the relay does not switch reliably
- Keep the relay on 5V power.
- Keep grounds common.
- Add a transistor / driver stage, or
- move relay control to the Pi GPIO and keep the ESP32 for sensors.


## Simulation profile

Until the real valve and camera are installed, you can safely run the software in a dry-run mode using `.env.simulation`. This keeps relay actions in software only and feeds Astra a synthetic camera image for testing health analysis and person-stop logic.
