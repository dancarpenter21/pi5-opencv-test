# Raspberry Pi 5 OpenCV Test

Stream a configured Camera Module 3 to a LAN browser, with red boxes around
faces detected by OpenCV. This is a standalone companion to `../pi5-camera-test`.

## Setup

Use Raspberry Pi OS with the native Picamera2 camera stack. Install the OS
packages (OpenCV and NumPy stay matched to the system camera libraries):

```bash
sudo apt install python3-picamera2 python3-opencv opencv-data
rpicam-hello --list-cameras
```

From this directory, create the project environment with the OS interpreter and
access to its camera packages. All Python commands run through `uv`:

```bash
uv venv --python /usr/bin/python3 --system-site-packages
uv sync --group dev
```

Picamera2, OpenCV, libcamera, and NumPy are OS dependencies; they are not installed
by `uv sync`. Flask and development dependencies are recorded in `uv.lock`.

## Run

```bash
uv run face-stream
```

Open `http://<pi-lan-address>:8000/` on the same network. The default is 640×480
at a target 15 fps, listening on `0.0.0.0:8000`. Detection and JPEG processing
can lower the actual frame rate. Stop with Ctrl+C.

```bash
uv run face-stream --host 0.0.0.0 --port 8080 --width 1280 --height 720 --fps 15
```

One camera worker captures, annotates, and encodes frames for all viewers.
Camera Module 3 continuous autofocus is enabled. `/` serves the preview page;
`/stream.mjpg` serves the annotated MJPEG stream. The browser server is intended
for a trusted LAN and has no authentication.

The bundled Haar cascade detects frontal faces best; profiles, small faces,
poor lighting, and occlusion can cause missed detections or false positives.
The app does not recognize people or save recordings.

## Tests

```bash
uv run pytest
```

Tests use fake camera input and require the OS OpenCV and NumPy packages, but
not a connected camera. For a hardware check, start the app, open the preview,
confirm red boxes on a visible face, then stop and restart to check camera cleanup.

## Troubleshooting

- Missing `cv2`, `picamera2`, or `libcamera`: install the prerequisites and recreate
  `.venv` with the setup command and `--system-site-packages`, then run `uv sync`.
- Missing classifier: install `opencv-data`; the app uses
  `/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml`.
- Camera unavailable: run `rpicam-hello --list-cameras`, check the ribbon cable,
  and stop other camera apps, including the sibling camera-stream server.
- Frozen preview: refresh the page and check server logs. A capture failure
  closes the stream and releases the camera; restart the app after fixing it.
- Port busy: stop the previous server or select another `--port`.
