from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, Deque, List
from collections import deque

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - if not installed
    YOLO = None  # type: ignore

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

@dataclass
class Detection:
    ts: float
    conf: float
    bbox: List[float]  # [x1, y1, x2, y2]
    cls: int

@dataclass
class HumanDetector:
    model_path: str
    conf_threshold: float
    debounce_frames: int
    min_positive_frames: int
    camera_index: int
    _model: Optional[object] = field(init=False, default=None)
    _buffer: Deque[Detection] = field(init=False, default_factory=lambda: deque(maxlen=50))

    def load(self) -> None:
        if YOLO is None:
            raise RuntimeError("Ultralytics YOLO not installed. Install 'ultralytics'.")
        self._model = YOLO(self.model_path)

    def _capture_frame(self, cap):  # type: ignore
        if cv2 is None:
            raise RuntimeError("opencv-python not installed.")
        ret, frame = cap.read()
        if not ret:
            return None
        return frame

    def detect(self) -> Optional[Detection]:
        if self._model is None:
            self.load()
        if cv2 is None:
            return None
        cap = getattr(self, '_cap', None)
        if cap is None:
            self._cap = cv2.VideoCapture(self.camera_index)
            cap = self._cap
        frame = self._capture_frame(cap)
        if frame is None:
            return None
        results = self._model(frame, verbose=False)  # type: ignore
        r0 = results[0]
        # Ultralytics result format: boxes.xyxy, boxes.cls, boxes.conf
        try:
            boxes = r0.boxes
            for xyxy, cls, conf in zip(boxes.xyxy, boxes.cls, boxes.conf):  # type: ignore
                c = int(cls.item())
                cf = float(conf.item())
                if c == 0 and cf >= self.conf_threshold:  # class 0 = person
                    det = Detection(time.time(), cf, xyxy.tolist(), c)
                    self._buffer.append(det)
                    if self._is_debounced():
                        return det
        except Exception:
            return None
        return None

    def _is_debounced(self) -> bool:
        # Count positives in last N frames
        recent = list(self._buffer)[-self.debounce_frames:]
        positives = [d for d in recent if d.conf >= self.conf_threshold]
        return len(positives) >= self.min_positive_frames
