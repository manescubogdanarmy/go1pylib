import argparse
import asyncio
import logging
import sys
from pathlib import Path

from go1pylib.go1 import Go1, Go1Mode

try:
    # If executed as module (python -m SnD.main)
    from .config import SearchConfig  # type: ignore
    from .controller import MissionController  # type: ignore
except ImportError:
    # Fallback: adjust path when run directly from SnD directory
    CURRENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_DIR.parent
    SRC_DIR = PROJECT_ROOT / 'src'
    if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    # Try absolute import after path injection
    from SnD.config import SearchConfig  # type: ignore
    from SnD.controller import MissionController  # type: ignore


def parse_args():
    p = argparse.ArgumentParser(description="Human Search & Detect Mission Controller")
    p.add_argument('--config', type=Path, default=Path(__file__).with_name('search_config.yaml'))
    p.add_argument('--simulation', action='store_true', help='Enable simulation mode (no real robot movement)')
    p.add_argument('--log-level', default=None)
    return p.parse_args()

async def async_main():
    args = parse_args()
    cfg = SearchConfig.load(args.config)
    if args.simulation:
        cfg.simulation.enabled = True
    if args.log_level:
        cfg.logging.level = args.log_level

    logging.basicConfig(level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
                        format='%(asctime)s - %(levelname)s - %(message)s')

    dog = Go1()
    dog.init()

    controller = MissionController(dog=dog, cfg=cfg)
    try:
        await controller.run()
    finally:
        try:
            dog.set_mode(Go1Mode.STAND_DOWN)
        except Exception:
            pass
        dog.mqtt.disconnect()


def main():  # entry point for console_scripts if desired later
    asyncio.run(async_main())

if __name__ == '__main__':
    main()
