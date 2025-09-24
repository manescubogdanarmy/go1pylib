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
class Circle:
    x: int
    y: int
    r: int

@dataclass
class DetectionEvent:
    ts: float
    camera: str
    circle: Circle

class HoughDetector:
    def __init__(self, blur_kernel: int, canny_low: int, canny_high: int, dp: float, min_dist: int, param1: int, param2: int, min_radius: int, max_radius: int):
        self.blur_kernel = blur_kernel
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.dp = dp
        self.min_dist = min_dist
        self.param1 = param1
        self.param2 = param2
        self.min_radius = min_radius
        self.max_radius = max_radius

    def detect(self, camera_name: str, frame) -> List[DetectionEvent]:
        if cv2 is None:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.blur_kernel > 0:
            gray = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, self.dp, self.min_dist,
                                   param1=self.param1, param2=self.param2,
                                   minRadius=self.min_radius, maxRadius=self.max_radius)
        out: List[DetectionEvent] = []
        if circles is not None:
            for (x, y, r) in circles[0, :]:
                out.append(DetectionEvent(time.time(), camera_name, Circle(int(x), int(y), int(r))))
        return out

def save_crop(frame, circle: Circle, out_path: Path):  # pragma: no cover
    h, w = frame.shape[:2]
    r = circle.r
    x1 = max(circle.x - r, 0)
    y1 = max(circle.y - r, 0)
    x2 = min(circle.x + r, w-1)
    y2 = min(circle.y + r, h-1)
    crop = frame[y1:y2, x1:x2]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), crop)
