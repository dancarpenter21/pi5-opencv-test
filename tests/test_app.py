import builtins
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from pi5_opencv_test.camera import CameraService, FrameBuffer
from pi5_opencv_test.detection import FaceDetector
from pi5_opencv_test.main import parse_args
from pi5_opencv_test.web import create_app


class Classifier:
    def empty(self):
        return False

    def detectMultiScale(self, gray, **kwargs):
        assert gray.ndim == 2
        return [(10, 15, 30, 35)]


def test_annotation():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    annotated = FaceDetector(Classifier()).annotate(frame)
    assert annotated[15, 10].tolist() == [0, 0, 255]
    assert annotated[50, 40].tolist() == [0, 0, 255]
    assert annotated[30, 25].tolist() == [0, 0, 0]


def test_multiple_consumers_and_close():
    buffer = FrameBuffer()
    first, second = buffer.frames(), buffer.frames()
    buffer.publish(b"first")
    assert next(first) == next(second) == b"first"
    buffer.publish(b"second")
    assert next(first) == next(second) == b"second"
    finished = threading.Event()
    thread = threading.Thread(target=lambda: (list(first), finished.set()))
    thread.start()
    buffer.close()
    thread.join(1)
    assert finished.is_set()
    assert list(second) == []


def test_web():
    buffer = FrameBuffer()
    buffer.publish(b"jpeg")
    app = create_app(SimpleNamespace(buffer=buffer, status="Streaming"))
    client = app.test_client()
    assert b"Pi 5 Face Detection" in client.get("/").data
    response = client.get("/stream.mjpg", buffered=False)
    assert response.mimetype == "multipart/x-mixed-replace"
    assert next(response.response) == b"--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg\r\n"
    response.close()
    buffer.close()


class FakeCamera:
    camera_controls = {}

    def __init__(self, fail=False):
        self.fail = fail
        self.closed = False
        self.stopped = False
        self.release = threading.Event()

    def create_video_configuration(self, **kwargs):
        return kwargs

    def configure(self, config):
        self.config = config

    def start(self):
        pass

    def capture_array(self, name):
        if self.fail:
            raise RuntimeError("capture failed")
        self.release.wait(0.01)
        return np.zeros((80, 80, 3), dtype=np.uint8)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


@pytest.mark.parametrize("fail", [False, True])
def test_camera_lifecycle(fail):
    camera = FakeCamera(fail)
    service = CameraService(camera_factory=lambda: camera, detector=FaceDetector(Classifier()))
    service.start()
    if fail:
        service._thread.join(2)
        assert service.error == "capture failed"
        assert list(service.buffer.frames()) == []
    else:
        assert next(service.buffer.frames()).startswith(b"\xff\xd8")
        assert camera.config["main"]["format"] == "RGB888"
    service.stop()
    assert camera.closed and camera.stopped
    assert not service._thread.is_alive()


@pytest.mark.parametrize("argv", [["--width", "0"], ["--fps", "-1"], ["--port", "65536"]])
def test_invalid_args(argv):
    with pytest.raises(SystemExit) as error:
        parse_args(argv)
    assert error.value.code == 2


def test_missing_dependency(monkeypatch, caplog):
    from pi5_opencv_test import main
    original_import = builtins.__import__

    def missing_cv2(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("cv2 unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(main, "parse_args", lambda: parse_args([]))
    monkeypatch.setattr(builtins, "__import__", missing_cv2)
    assert main.main() == 1
    assert "--system-site-packages" in caplog.text
