from __future__ import annotations
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore

@dataclass
class CircleDetection:
    ts: float
    center_x: int
    center_y: int
    radius: int
    strength: float  # derived from accumulator or heuristic

class CircleDetector:
    def __init__(self, camera_index: int = 0, blur_kernel: int = 5,
                 canny_low: int = 50, canny_high: int = 150,
                 dp: float = 1.2, min_dist: int = 40,
                 param1: int = 120, param2: int = 30,
                 min_radius: int = 10, max_radius: int = 160):
        self.camera_index = camera_index
        self.blur_kernel = blur_kernel
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.dp = dp
        self.min_dist = min_dist
        self.param1 = param1
        self.param2 = param2
        self.min_radius = min_radius
        self.max_radius = max_radius
        self._cap = None

    def _ensure_camera(self):
        if cv2 is None:
            raise RuntimeError("opencv-python not installed")
        if self._cap is None:
            self._cap = cv2.VideoCapture(self.camera_index)
            if not self._cap.isOpened():
                raise RuntimeError("Unable to open camera index %d" % self.camera_index)

    def capture_and_detect(self) -> List[CircleDetection]:
        if cv2 is None:
            return []
        self._ensure_camera()
        ret, frame = self._cap.read()
        if not ret:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.blur_kernel > 0:
            gray = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        # Use HoughCircles directly on blurred gray to leverage gradient info
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, self.dp, self.min_dist,
                                   param1=self.param1, param2=self.param2,
                                   minRadius=self.min_radius, maxRadius=self.max_radius)
        detections: List[CircleDetection] = []
        if circles is not None:
            circles = circles[0, :]
            for (x, y, r) in circles:
                detections.append(CircleDetection(time.time(), int(x), int(y), int(r), strength=float(r)))
        self._last_frame = frame  # store for GUI overlay & saving
        self._last_edges = edges
        return detections

    def last_frame(self):  # returns latest BGR frame
        return getattr(self, '_last_frame', None)

    def close(self):  # pragma: no cover - hardware cleanup
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass
