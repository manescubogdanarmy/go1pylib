from __future__ import annotations
import threading
import queue
from typing import Optional, Dict, Any

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

class CamWorker:
    def __init__(self, name: str, uri: str, width: Optional[int] = None, height: Optional[int] = None, rotate_deg: int = 0):
        self.name = name
        self.uri = uri
        self.width = width
        self.height = height
        self.rotate_deg = rotate_deg
        self._cap = None
        self._thread: Optional[threading.Thread] = None
        self.frames: "queue.Queue" = queue.Queue(maxsize=1)  # latest frame semantics
        self._stop = False

    def start(self):  # pragma: no cover
        if cv2 is None:
            raise RuntimeError("OpenCV not installed")
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):  # pragma: no cover
        self._cap = self._open_capture(self.uri)
        while not self._stop and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                # try reopen
                self._cap.release()
                self._cap = self._open_capture(self.uri)
                continue
            if self.rotate_deg:
                if self.rotate_deg == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif self.rotate_deg == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif self.rotate_deg == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # latest only
            try:
                if self.frames.full():
                    _ = self.frames.get_nowait()
                self.frames.put_nowait(frame)
            except queue.Full:
                pass

    def _open_capture(self, uri: str):  # pragma: no cover
        # allow int indices
        if uri.isdigit():
            cap = cv2.VideoCapture(int(uri))
        else:
            # For UDP sources, prefer FFmpeg backend and add larger FIFO to reduce drops
            if uri.startswith("udp://"):
                u = uri
                if "?" not in u:
                    # overrun_nonfatal/fifo_size are FFmpeg UDP demuxer options
                    u = f"{u}?overrun_nonfatal=1&fifo_size=50000000"
                try:
                    cap = cv2.VideoCapture(u, cv2.CAP_FFMPEG)
                except Exception:
                    cap = cv2.VideoCapture(u)
            else:
                cap = cv2.VideoCapture(uri)
        if self.width is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return cap

    def get_latest(self):
        try:
            return self.frames.get_nowait()
        except queue.Empty:
            return None

    def stop(self):  # pragma: no cover
        self._stop = True
        try:
            if self._thread:
                self._thread.join(timeout=1)
        except Exception:
            pass
        try:
            if self._cap:
                self._cap.release()
        except Exception:
            pass
