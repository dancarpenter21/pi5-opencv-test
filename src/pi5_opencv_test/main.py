"""Command-line entry point."""

import argparse
import logging

from .camera import CameraService
from .web import create_app


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stream Camera Module 3 with red face boxes.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args(argv)
    if min(args.width, args.height, args.fps) <= 0 or not 1 <= args.port <= 65535:
        parser.error("width, height, and fps must be positive; port must be 1–65535")
    return args


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    camera = CameraService(args.width, args.height, args.fps)
    try:
        camera.start()
    except ImportError as error:
        logging.error("Missing camera dependency: %s. Install python3-picamera2, python3-opencv, "
                      "and opencv-data; create the uv environment with --system-site-packages.", error)
        return 1
    except Exception as error:
        logging.error("Could not start camera: %s. Check rpicam-hello --list-cameras "
                      "and stop other camera applications.", error)
        return 1
    try:
        create_app(camera).run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    finally:
        camera.stop()
    return 1 if camera.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
