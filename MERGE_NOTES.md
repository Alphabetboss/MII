# Merge notes

## Major improvements added in this merged build

1. **Autonomous scheduler**
   - The original repos had scheduling pieces, but no clean, safe autonomous service loop.
   - This build adds a background thread that evaluates schedule, sensor data, camera health, and safety conditions.

2. **People detection shutoff**
   - The original repos described this feature but did not implement a reliable end-to-end version.
   - This build adds OpenCV HOG-based person detection and stops water if someone enters the spray area.

3. **Pressure safety shutoff**
   - The repos referenced burst / standing-water protection but were fragmented.
   - This build includes a unified pressure safety check with configurable PSI thresholds.

4. **Decision logging**
   - Every autonomous run decision is written to `logs/decision_log.jsonl`.
   - This gives Astra a real audit trail for each runtime adjustment.

5. **Camera health analysis**
   - The best color-thresholding logic was merged and cleaned into one camera pipeline.
   - Optional YOLO support is kept, but the system still works without custom weights.

## Things still needing your exact hardware details

- exact SparkFun board model
- exact pressure sensor model
- exact moisture sensor model
- exact camera type / connection path
- whether your relay board is active-low or active-high


## Pi 5 + ESP32 pass
- Added serial field-controller bridge for SparkFun ESP32 Thing Plus
- Added one-zone ESP32 firmware sketch for DHT11 + relay control
- Added NVMe-friendly data root configuration
- Added touchscreen kiosk launcher script
