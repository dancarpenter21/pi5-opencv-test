"""Browser preview and MJPEG endpoint."""

from flask import Flask, Response, render_template


def create_app(camera):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", status=camera.status)

    @app.get("/stream.mjpg")
    def stream():
        def frames():
            for frame in camera.buffer.frames():
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store"})

    return app
