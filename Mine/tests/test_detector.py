from pathlib import Path
import sys, pathlib

# Ensure project root on sys.path for direct package import
root = pathlib.Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from Mine.detector import CircleDetector  # type: ignore

# Basic smoke test (no camera requirement) - we monkeypatch capture

def test_circle_detector_init():
    det = CircleDetector(camera_index=0)
    assert det.camera_index == 0
    assert det.min_radius < det.max_radius
