# YIIOT CB101 Wi-Fi Camera Notes

What changed in this build:
- Astra can now read a network camera from `II_CAMERA_URL`.
- If the URL is `http://` or `https://`, the app first tries to fetch a still snapshot image.
- If that fails, it falls back to OpenCV video capture, which can work with RTSP/HTTP streams that OpenCV supports.

Suggested setup:
1. Keep simulation on while you test the UI.
2. When you are ready, copy `.env.laptop_dev` to `.env`.
3. Set `II_CAMERA_SIMULATE=0`.
4. Set `II_CAMERA_URL=` to the camera's direct stream or snapshot URL.

Important reality check:
- Many YI / YI IoT cameras do not expose an official RTSP or ONVIF stream in the stock app/firmware.
- If your CB101 only works inside the YI IoT app, Astra cannot read it directly until you have a direct LAN URL (snapshot, MJPEG, or RTSP) or you switch to a camera/NVR that exposes one.

Safe path:
- Keep Astra on simulation for now.
- When you discover a direct camera URL, drop it into `II_CAMERA_URL` and Astra will use Wi-Fi capture instead of a USB camera index.
