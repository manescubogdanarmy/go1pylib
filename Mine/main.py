from __future__ import annotations
import argparse
import logging
import time
import sys
from pathlib import Path
from .config import MineConfig
from .detector import CircleDetector
from .telemetry import MineTelemetryLogger
from .gui import LabelGUI

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger("mine")

def parse_args():
    ap = argparse.ArgumentParser(description="Mine-like round object detection & labeling")
    ap.add_argument('--config', type=str, default=None, help='Path to mine_config.yaml')
    ap.add_argument('--simulation', action='store_true', help='Simulation mode (no robot required)')
    return ap.parse_args()

def run(cfg: MineConfig):
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

if __name__ == '__main__':
    args = parse_args()
    cfg = MineConfig.load(Path(args.config) if args.config else None)
    run(cfg)
