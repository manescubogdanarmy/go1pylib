from __future__ import annotations
import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from go1pylib.go1 import Go1, Go1Mode
from SnD.lane_planner import generate_lanes, Lane
from SnD.pose import Pose, apply_forward, apply_turn
from .detector import CircleDetector, CircleDetection
from .gui import LabelGUI
from .telemetry import MineTelemetryLogger
from .config import MineConfig
import contextlib
import asyncio

logger = logging.getLogger(__name__)

STATE_INIT = "INIT"
STATE_SEARCH = "SEARCH"
STATE_LABEL = "LABEL"
STATE_COMPLETE = "COMPLETE"
STATE_FAILSAFE = "FAILSAFE"

@dataclass
class CommandRecord:
    kind: str
    speed: float
    duration_ms: int

@dataclass
class MineMissionController:
    dog: Go1
    cfg: MineConfig
    detector: CircleDetector
    gui: LabelGUI
    telemetry: Optional[MineTelemetryLogger] = None
    pose: Pose = field(default_factory=Pose)
    state: str = STATE_INIT
    command_log: List[CommandRecord] = field(default_factory=list)
    _lanes: List[Lane] = field(default_factory=list)
    _stop: bool = False

    async def run(self):
        logger.info("Mine auto-search mission starting")
        try:
            # Check robot connection status
            if hasattr(self.dog, 'mqtt'):
                logger.info(f"Robot MQTT connected: {getattr(self.dog.mqtt, 'connected', False)}")
                if not getattr(self.dog.mqtt, 'connected', False):
                    logger.error("Robot MQTT not connected. Aborting mission.")
                    return
            logger.info("Setting robot mode to WALK...")
            with contextlib.suppress(Exception):
                self.dog.set_mode(Go1Mode.WALK)
            logger.info("Robot mode set. Sleeping 1s...")
            await asyncio.sleep(1.0)
            logger.info("Generating lanes...")
            self._lanes = generate_lanes(self.cfg.area.width_m, self.cfg.area.height_m, self.cfg.area.lane_width_m)
            self.state = STATE_SEARCH
            if self.cfg.logging.telemetry and self.telemetry is None:
                import datetime
                stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                self.telemetry = MineTelemetryLogger(Path(self.cfg.logging.telemetry_dir)/f"mine_auto_{stamp}.csv",
                                                     fieldnames=["ts","state","x","y","heading","cmd","speed","duration_ms","detections"])
            logger.info("Starting search loop...")
            await self._search_loop()
            self.state = STATE_COMPLETE
            logger.info("Mine mission complete")
        except asyncio.CancelledError:  # pragma: no cover
            logger.info("Mission cancelled")
        except KeyboardInterrupt:  # pragma: no cover
            logger.info("Mission interrupted by user")
        finally:
            if self.telemetry:
                self.telemetry.close()

    async def _search_loop(self):
        for lane in self._lanes:
            if self.state != STATE_SEARCH:
                break
            await self._execute_lane(lane)
        if self.state == STATE_SEARCH:
            self.state = STATE_COMPLETE

    async def _execute_lane(self, lane: Lane):
        distance = lane.length
        remaining = distance
        speed_fraction = self.cfg.movement.walk_speed_fraction
        speed_mps = speed_fraction * self.cfg.movement.max_search_speed_mps
        pulse_m = self.cfg.movement.forward_pulse_m
        while remaining > 0 and self.state == STATE_SEARCH:
            step = min(pulse_m, remaining)
            duration_ms = int((step / speed_mps) * 1000) if speed_mps > 1e-6 else 0
            await self._forward(speed_fraction, duration_ms, note=f"lane_{lane.index}")
            apply_forward(self.pose, step)
            remaining -= step
            # vision check after each pulse
            dets = self.detector.capture_and_detect()
            if dets:
                await self._handle_detections(dets)
            await asyncio.sleep(0)  # yield
        if self.state == STATE_SEARCH and lane != self._lanes[-1]:
            await self._lane_transition()

    async def _forward(self, speed: float, duration_ms: int, note: str = ""):
        if self.cfg.simulation.enabled:
            await asyncio.sleep(duration_ms/1000)
        else:
            await self.dog.go_forward(speed, duration_ms)
        self.command_log.append(CommandRecord('forward', speed, duration_ms))
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='forward', speed=speed, duration_ms=duration_ms, detections=0)

    async def _turn_right(self):
        dur = self.cfg.movement.turn_90_ms
        if self.cfg.simulation.enabled:
            await asyncio.sleep(dur/1000)
        else:
            await self.dog.turn_right(self.cfg.movement.walk_speed_fraction, dur)
        self.command_log.append(CommandRecord('turn_right', self.cfg.movement.walk_speed_fraction, dur))
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='turn_right', speed=self.cfg.movement.walk_speed_fraction, duration_ms=dur, detections=0)

    async def _lane_transition(self):
        await self._turn_right()
        await self._forward(self.cfg.movement.walk_speed_fraction, int(0.5 / max(1e-6, (self.cfg.movement.walk_speed_fraction * self.cfg.movement.max_search_speed_mps)) * 1000))
        await self._turn_right()
        apply_turn(self.pose, -math.pi/2)
        apply_forward(self.pose, 0.5)
        apply_turn(self.pose, -math.pi/2)

    async def _handle_detections(self, dets: List[CircleDetection]):
        logger.info(f"Detected {len(dets)} circular object(s); entering LABEL state")
        self.state = STATE_LABEL
        frame = self.detector.last_frame()
        if frame is not None:
            self.gui.submit(frame, dets)
        # Wait for a short labeling window
        await self._label_wait_loop(timeout_s=8.0)
        if self.state == STATE_LABEL:
            self.state = STATE_SEARCH

    async def _label_wait_loop(self, timeout_s: float):
        import time
        start = time.time()
        while time.time() - start < timeout_s and self.state == STATE_LABEL:
            await asyncio.sleep(0.25)

    def stop(self):  # pragma: no cover
        self._stop = True
        if self.telemetry:
            self.telemetry.close()