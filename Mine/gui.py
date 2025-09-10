from __future__ import annotations
import threading
import queue
from pathlib import Path
from typing import List, Optional, Callable

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

class LabelGUI:
    """Simple OpenCV based GUI to visualize detections and accept user validation.

    Keys:
      y - mark highlighted circle as correct (mine)
      n - mark highlighted circle as incorrect (not a mine)
      q - quit session
      s - skip current frame

    Each detection is saved into appropriate folder (correct/incorrect) with the raw frame cropped.
    """
    def __init__(self, save_dir: Path, on_label: Optional[Callable[[dict], None]] = None):
        self.save_dir = save_dir
        self.on_label = on_label
        self.save_dir.mkdir(parents=True, exist_ok=True)
        # Folders align with user request: separate mine vs not_mine
        (self.save_dir / 'mine').mkdir(exist_ok=True)
        (self.save_dir / 'not_mine').mkdir(exist_ok=True)
        self._queue = queue.Queue()
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def submit(self, frame, detections):  # frame BGR, detections list of CircleDetection
        if cv2 is None:
            return
        self._queue.put((frame, detections))

    def _loop(self):  # pragma: no cover - interactive loop
        if cv2 is None:
            return
        idx = 0
        while not self._stop:
            try:
                frame, dets = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                continue
            display = frame.copy()
            for i, d in enumerate(dets):
                color = (0, 255, 0) if i == 0 else (0, 200, 255)
                cv2.circle(display, (d.center_x, d.center_y), d.radius, color, 2)
                cv2.putText(display, f"r={d.radius}", (d.center_x+5, d.center_y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            cv2.putText(display, "y=yes n=no s=skip q=quit", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.imshow("Mine Detection", display)
            key = cv2.waitKey(0) & 0xFF
            if key == ord('q'):
                self._stop = True
                break
            if not dets:
                continue
            label = None
            if key == ord('y'):
                label = 'mine'
            elif key == ord('n'):
                label = 'not_mine'
            elif key == ord('s'):
                continue
            if label:
                # save first detection crop
                d = dets[0]
                h, w = frame.shape[:2]
                r = d.radius
                x1 = max(d.center_x - r, 0)
                y1 = max(d.center_y - r, 0)
                x2 = min(d.center_x + r, w-1)
                y2 = min(d.center_y + r, h-1)
                crop = frame[y1:y2, x1:x2]
                out_path = self.save_dir / label / f"det_{idx:05d}.png"
                cv2.imwrite(str(out_path), crop)
                if self.on_label:
                    self.on_label({'path': str(out_path), 'label': label, 'radius': d.radius})
                idx += 1
        cv2.destroyAllWindows()

    def stop(self):  # pragma: no cover
        self._stop = True
        try:
            self._thread.join(timeout=1)
        except Exception:
            pass
