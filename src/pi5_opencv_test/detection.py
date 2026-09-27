"""OpenCV frontal-face detection and annotation."""

from pathlib import Path


class FaceDetector:
    def __init__(self, classifier=None):
        import cv2

        self.cv2 = cv2
        if classifier is None:
            path = Path("/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")
            if not path.is_file():
                raise RuntimeError("Missing face classifier; install opencv-data with apt.")
            classifier = cv2.CascadeClassifier(str(path))
        if classifier.empty():
            raise RuntimeError("Could not load the face classifier.")
        self.classifier = classifier

    def annotate(self, frame):
        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        gray = self.cv2.equalizeHist(gray)
        faces = self.classifier.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        for x, y, width, height in faces:
            self.cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 255), 2)
        return frame
