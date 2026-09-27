"""Single camera worker and latest-frame delivery to browser clients."""

import logging
import threading


class FrameBuffer:
    def __init__(self):
        self._condition = threading.Condition()
        self._frame = None
        self._sequence = 0
        self._closed = False

    def publish(self, frame):
        with self._condition:
            if not self._closed:
                self._frame = bytes(frame)
                self._sequence += 1
                self._condition.notify_all()

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def frames(self):
        sequence = 0
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._sequence != sequence)
                if self._closed:
                    return
                sequence = self._sequence
                frame = self._frame
            yield frame


class CameraService:
    def __init__(self, width=640, height=480, fps=15, *, camera_factory=None, detector=None):
        self.width, self.height, self.fps = width, height, fps
        self.buffer = FrameBuffer()
        self.error = None
        self._factory = camera_factory
        self._detector = detector
        self._camera = None
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        import cv2
        from .detection import FaceDetector

        self._cv2 = cv2
        self._detector = self._detector or FaceDetector()
        if self._factory is None:
            from picamera2 import Picamera2
            self._factory = Picamera2
        camera = self._factory()
        self._camera = camera
        try:
            controls = {"FrameRate": self.fps}
            if "AfMode" in camera.camera_controls:
                from libcamera import controls as camera_controls
                controls["AfMode"] = camera_controls.AfModeEnum.Continuous
            config = camera.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls=controls,
            )
            camera.configure(config)
            camera.start()
            self._thread = threading.Thread(target=self._run, name="face-camera", daemon=True)
            self._thread.start()
        except Exception:
            camera.close()
            self._camera = None
            self.buffer.close()
            raise

    def _run(self):
        try:
            while not self._stop.is_set():
                frame = self._camera.capture_array("main")
                frame = self._detector.annotate(frame)
                ok, encoded = self._cv2.imencode(".jpg", frame)
                if not ok:
                    raise RuntimeError("JPEG encoding failed")
                self.buffer.publish(encoded.tobytes())
        except Exception as error:
            if not self._stop.is_set():
                self.error = str(error)
                logging.exception("Camera stream failed")
        finally:
            self.buffer.close()
            try:
                self._camera.stop()
            finally:
                self._camera.close()

    def stop(self):
        self._stop.set()
        self.buffer.close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logging.warning("Camera worker did not stop within five seconds")

    @property
    def status(self):
        if self.error:
            return "Camera stream failed; check server logs."
        if self._thread is not None and self._thread.is_alive() and not self._stop.is_set():
            return "Streaming"
        return "Stopped"
