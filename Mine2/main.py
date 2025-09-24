from __future__ import annotations
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List

from .config import Mine2Config
from .streams import CamWorker
from .detector import HoughDetector, save_crop
from .gui import MultiFeedGUI
from .telemetry import Telemetry

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger("mine2")

def parse_args():
    ap = argparse.ArgumentParser(description="Mine2 multi-camera round-object monitoring (Windows)")
    ap.add_argument('--config', type=str, required=True, help='Path to Mine2 config YAML')
    return ap.parse_args()

def run(cfg: Mine2Config):
    # Set logging level
    logger.setLevel(getattr(logging, cfg.logging_level.upper(), logging.INFO))

    # Start cameras
    workers: Dict[str, CamWorker] = {}
    for cam in cfg.cameras:
        if not cam.enabled:
            continue
        w = CamWorker(cam.name, cam.uri, cam.width, cam.height, cam.rotate_deg)
        w.start()
        workers[cam.name] = w
        logger.info(f"Started camera {cam.name} -> {cam.uri}")

    # Detector
    vp = cfg.vision
    det = HoughDetector(vp.blur_kernel, vp.canny_low, vp.canny_high, vp.dp, vp.min_dist, vp.param1, vp.param2, vp.min_radius, vp.max_radius)

    # Telemetry
    import datetime
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    tlog = Telemetry(Path('Mine2/logs')/f"mine2_{stamp}.csv", fieldnames=['ts','camera','x','y','r','saved'])

    # GUI
    gui = MultiFeedGUI("Mine2 Monitoring")
    page = 0
    names = sorted(workers.keys())
    pages = max(1, (len(names)+3)//4)
    logger.info(f"Cameras: {names}; pages={pages}")

    try:
        while True:
            # Collect latest frames
            frames = {name: w.get_latest() for name,w in workers.items()}
            detections_px: Dict[str, List[tuple]] = {name: [] for name in workers.keys()}
            # Detect per frame (passive; non-blocking display continues)
            for name, frame in frames.items():
                if frame is None:
                    continue
                events = det.detect(name, frame)
                for ev in events:
                    detections_px[name].append((ev.circle.x, ev.circle.y, ev.circle.r))
                    logger.info(f"Detected circle on {name} at ({ev.circle.x},{ev.circle.y}) r={ev.circle.r}")
                    # Save unsorted crop
                    out_root = Path(cfg.dataset.unsorted_dir)/name
                    out_path = out_root / f"{int(ev.ts)}_{ev.circle.x}_{ev.circle.y}_{ev.circle.r}.png"
                    save_crop(frame, ev.circle, out_path)
                    tlog.log(camera=name, x=ev.circle.x, y=ev.circle.y, r=ev.circle.r, saved=str(out_path))

            key = gui.draw(frames, detections_px, page=page)
            if key == ord('q'):
                break
            elif key == ord('['):
                page = (page - 1) % pages
            elif key == ord(']'):
                page = (page + 1) % pages
            elif key == ord('s'):
                # Save full frames for current page cameras under unsorted
                for name in names[page*4:page*4+4]:
                    f = frames.get(name)
                    if f is None: continue
                    out_root = Path(cfg.dataset.unsorted_dir)/name
                    out_root.mkdir(parents=True, exist_ok=True)
                    out_path = out_root / f"full_{int(time.time())}.png"
                    cv2.imwrite(str(out_path), f)
                    logger.info(f"Saved full frame {out_path}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        for w in workers.values():
            w.stop()
        tlog.close()
        gui.close()

if __name__ == '__main__':
    args = parse_args()
    cfg = Mine2Config.load(Path(args.config))
    run(cfg)
