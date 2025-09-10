from __future__ import annotations
import argparse
import logging
import time
import sys
from pathlib import Path

# Support running as a script (python Mine/main.py) and as a module (python -m Mine.main)
if __package__ is None or __package__ == "":  # script execution
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # Use absolute imports after ensuring root path
    from Mine.config import MineConfig  # type: ignore
    from Mine.detector import CircleDetector  # type: ignore
    from Mine.telemetry import MineTelemetryLogger  # type: ignore
    from Mine.gui import LabelGUI  # type: ignore
    from Mine.mission import MineMissionController  # type: ignore
else:  # package context
    from .config import MineConfig
    from .detector import CircleDetector
    from .telemetry import MineTelemetryLogger
    from .gui import LabelGUI
    from .mission import MineMissionController

from go1pylib.go1 import Go1, Go1Mode

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger("mine")

def parse_args():
    ap = argparse.ArgumentParser(description="Mine-like round object detection & labeling")
    ap.add_argument('--config', type=str, default=None, help='Path to mine_config.yaml')
    ap.add_argument('--simulation', action='store_true', help='Simulation mode (no robot movement)')
    ap.add_argument('--auto-search', action='store_true', help='Enable autonomous lawn-mower style search')
    return ap.parse_args()

def run_manual(cfg: MineConfig):
    logger.info("Starting Mine detection session")
    det = CircleDetector(camera_index=cfg.vision.camera_index,
                         blur_kernel=cfg.vision.blur_kernel,
                         canny_low=cfg.vision.canny_low,
                         canny_high=cfg.vision.canny_high,
                         dp=cfg.vision.dp,
                         min_dist=cfg.vision.min_dist,
                         param1=cfg.vision.param1,
                         param2=cfg.vision.param2,
                         min_radius=cfg.vision.min_radius,
                         max_radius=cfg.vision.max_radius)
    # Telemetry
    import datetime
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    tlog = MineTelemetryLogger(Path(cfg.logging.telemetry_dir)/f"mine_session_{stamp}.csv",
                               fieldnames=['ts','num_detections','latency_ms']) if cfg.logging.telemetry else None

    gui = LabelGUI(Path(cfg.vision.save_dir))

    try:
        while True:
            start = time.time()
            detections = det.capture_and_detect()
            latency_ms = int((time.time()-start)*1000)
            if tlog:
                tlog.log(num_detections=len(detections), latency_ms=latency_ms)
            frame = det.last_frame()
            if frame is not None and detections:
                gui.submit(frame, detections)
            # Show a lightweight live window even when no detections
            if frame is not None and not detections:
                if cfg.vision.enabled and hasattr(sys.modules.get('cv2'), 'imshow'):
                    import cv2  # type: ignore
                    view = frame.copy()
                    cv2.putText(view, 'Scanning...', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
                    cv2.imshow('Mine Detection', view)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            time.sleep(0.05)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:  # cleanup
        det.close()
        if tlog:
            tlog.close()
        gui.stop()

def run_auto(cfg: MineConfig):
    if cfg.simulation.enabled:
        # Lightweight fake dog for simulation without MQTT connection
        class FakeDog:  # pragma: no cover - simple simulation
            def set_mode(self, mode):
                return
            async def go_forward(self, speed: float, duration_ms: int):
                await asyncio.sleep(duration_ms/1000)
            async def turn_right(self, speed: float, duration_ms: int):
                await asyncio.sleep(duration_ms/1000)
        dog = FakeDog()
    else:
        dog = Go1()
        dog.init()
    det = CircleDetector(camera_index=cfg.vision.camera_index,
                         blur_kernel=cfg.vision.blur_kernel,
                         canny_low=cfg.vision.canny_low,
                         canny_high=cfg.vision.canny_high,
                         dp=cfg.vision.dp,
                         min_dist=cfg.vision.min_dist,
                         param1=cfg.vision.param1,
                         param2=cfg.vision.param2,
                         min_radius=cfg.vision.min_radius,
                         max_radius=cfg.vision.max_radius)
    gui = LabelGUI(Path(cfg.vision.save_dir))
    controller = MineMissionController(dog=dog, cfg=cfg, detector=det, gui=gui)
    import asyncio
    asyncio.run(controller.run())

if __name__ == '__main__':
    args = parse_args()
    cfg = MineConfig.load(Path(args.config) if args.config else None)
    if args.simulation:
        cfg.simulation.enabled = True
    if args.auto_search:
        run_auto(cfg)
    else:
        run_manual(cfg)
