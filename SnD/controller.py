from __future__ import annotations
import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from go1pylib.go1 import Go1, Go1Mode
from go1pylib.mqtt.state import Go1State

from .config import SearchConfig
from .lane_planner import generate_lanes, Lane
from .pose import Pose, apply_forward, apply_turn
from .vision import HumanDetector, Detection
from .telemetry import TelemetryLogger

logger = logging.getLogger(__name__)

STATE_INIT = 'INIT'
STATE_SEARCH = 'SEARCH'
STATE_APPROACH = 'APPROACH'
STATE_INTERACT = 'INTERACT'
STATE_RETURN = 'RETURN'
STATE_COMPLETE = 'COMPLETE'
STATE_FAILSAFE = 'FAILSAFE'

@dataclass
class CommandRecord:
    kind: str  # forward | turn_left | turn_right
    speed: float
    duration_ms: int

@dataclass
class MissionController:
    dog: Go1
    cfg: SearchConfig
    pose: Pose = field(default_factory=Pose)
    state: str = STATE_INIT
    command_log: List[CommandRecord] = field(default_factory=list)
    detection: Optional[Detection] = None
    _lanes: List[Lane] = field(default_factory=list)
    _stop: bool = False
    _battery_ok: bool = True
    _last_state_emit: float = 0.0
    detector: Optional[HumanDetector] = None
    telemetry: Optional[TelemetryLogger] = None
    fake_detection: bool = False  # for test hook
    collision_block: bool = False

    def setup_events(self) -> None:
        def on_state(go1_state: Go1State):  # battery monitoring
            try:
                soc = go1_state.bms.soc
                if self.state == STATE_INIT and soc < self.cfg.safety.min_battery_start_pct:
                    logger.error("Battery too low to start mission.")
                    self._battery_ok = False
                if soc < self.cfg.safety.min_battery_runtime_pct:
                    logger.warning("Battery below runtime minimum – triggering failsafe.")
                    self.state = STATE_FAILSAFE
                # distance warnings (collision avoidance) if enabled
                if self.cfg.safety.enable_collision_adapter:
                    try:
                        warnings = go1_state.robot.distance_warning
                        if (warnings.front < 0.75) or (warnings.left < 0.5) or (warnings.right < 0.5):
                            self.collision_block = True
                        else:
                            self.collision_block = False
                    except Exception:
                        pass
            except Exception:
                pass
        self.dog.on('go1_state_change', on_state)

    async def run(self) -> None:
        logger.info("Mission starting")
        self.setup_events()
        if not self._battery_ok:
            self.state = STATE_FAILSAFE
        else:
            await self._ensure_connection()
        if self.state == STATE_FAILSAFE:
            await self._stop_all()
            return
        self.dog.set_mode(Go1Mode.WALK)
        await asyncio.sleep(2)
        self._lanes = generate_lanes(self.cfg.area.width_m, self.cfg.area.height_m, self.cfg.area.lane_width_m)
        self.state = STATE_SEARCH
        if self.cfg.logging.telemetry:
            import datetime
            stamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            from pathlib import Path
            self.telemetry = TelemetryLogger(Path(self.cfg.logging.telemetry_dir)/f"session_{stamp}.csv",
                                            fieldnames=["ts","state","x","y","heading","cmd","speed","duration_ms","note"])
        if self.cfg.vision.enabled:
            self.detector = HumanDetector(
                model_path=self.cfg.vision.model,
                conf_threshold=self.cfg.vision.conf_threshold,
                debounce_frames=self.cfg.vision.debounce_frames,
                min_positive_frames=self.cfg.vision.min_positive_frames,
                camera_index=self.cfg.vision.camera_index,
            )
        await self._mission_loop()

    async def _mission_loop(self):
        vision_task = None
        if self.detector:
            vision_task = asyncio.create_task(self._vision_loop())
        try:
            await self._search_loop()
        finally:
            if vision_task:
                vision_task.cancel()
                with contextlib.suppress(Exception):
                    await vision_task

    async def _ensure_connection(self):
        logger.info("Ensuring connection...")
        start = time.time()
        timeout = 10
        while not self.dog.mqtt.connected and time.time() - start < timeout:
            await asyncio.sleep(0.1)
        if not self.dog.mqtt.connected:
            logger.error("Connection failed")
            self.state = STATE_FAILSAFE

    async def _search_loop(self):
        for lane in self._lanes:
            if self.state != STATE_SEARCH:
                break
            await self._execute_lane(lane)
        if self.state == STATE_SEARCH:
            logger.info("Search complete without detection; returning to start.")
            self.state = STATE_RETURN
            await self._return_to_start()
            self.state = STATE_COMPLETE

    async def _execute_lane(self, lane: Lane):
        distance = lane.length
        remaining = distance
        speed_fraction = self.cfg.movement.walk_speed_fraction
        speed_mps = speed_fraction * self.cfg.movement.max_search_speed_mps
        pulse_m = self.cfg.movement.forward_pulse_m
        while remaining > 0 and self.state == STATE_SEARCH:
            step = min(pulse_m, remaining)
            duration_ms = int((step / speed_mps) * 1000)
            await self._forward(speed_fraction, duration_ms, note=f"lane_{lane.index}")
            apply_forward(self.pose, step)
            remaining -= step
            await asyncio.sleep(0)  # yield
        if self.state == STATE_SEARCH:
            # turn to next lane if not last
            if lane != self._lanes[-1]:
                await self._lane_transition()

    async def _lane_transition(self):
        # 90 degree turn, small forward, 90 degree turn
        await self._turn_right()
        await self._forward(self.cfg.movement.walk_speed_fraction, int(0.5 / (self.cfg.movement.walk_speed_fraction * self.cfg.movement.max_search_speed_mps) * 1000))
        await self._turn_right()
        # update pose roughly
        apply_turn(self.pose, -math.pi/2)
        apply_forward(self.pose, 0.5)
        apply_turn(self.pose, -math.pi/2)

    async def _forward(self, speed: float, duration_ms: int, note: str = ""):
        if self.collision_block:
            logger.warning("Collision block active; skipping forward pulse")
            await asyncio.sleep(0.2)
            return
        if self.cfg.simulation.enabled:
            await asyncio.sleep(duration_ms / 1000)
        else:
            await self.dog.go_forward(speed, duration_ms)
        self.command_log.append(CommandRecord('forward', speed, duration_ms))
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='forward', speed=speed, duration_ms=duration_ms, note=note)

    async def _turn_right(self):
        dur = self.cfg.movement.turn_90_ms
        if self.cfg.simulation.enabled:
            await asyncio.sleep(dur/1000)
        else:
            await self.dog.turn_right(self.cfg.movement.walk_speed_fraction, dur)
        self.command_log.append(CommandRecord('turn_right', self.cfg.movement.walk_speed_fraction, dur))
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='turn_right', speed=self.cfg.movement.walk_speed_fraction, duration_ms=dur, note="")

    async def _turn_left(self):
        dur = self.cfg.movement.turn_90_ms
        if self.cfg.simulation.enabled:
            await asyncio.sleep(dur/1000)
        else:
            await self.dog.turn_left(self.cfg.movement.walk_speed_fraction, dur)
        self.command_log.append(CommandRecord('turn_left', self.cfg.movement.walk_speed_fraction, dur))
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='turn_left', speed=self.cfg.movement.walk_speed_fraction, duration_ms=dur, note="")

    async def _vision_loop(self):
        assert self.detector
        while self.state in (STATE_SEARCH, STATE_APPROACH):
            if self.fake_detection and self.state == STATE_SEARCH:
                # create synthetic detection once
                from .vision import Detection
                det = Detection(time.time(), 0.99, [0,0,10,10], 0)
                self.fake_detection = False
            else:
                det = self.detector.detect()
            if det and self.state == STATE_SEARCH:
                logger.info(f"Human detected conf={det.conf:.2f}; switching to APPROACH")
                self.detection = det
                self.state = STATE_APPROACH
                await self._approach_loop()
                if self.state != STATE_FAILSAFE:
                    break
            await asyncio.sleep(0.05)

    async def _approach_loop(self):
        # naive approach: forward pulses limited by count (no real range estimation yet)
        max_pulses = 15
        pulses = 0
        while self.state == STATE_APPROACH and pulses < max_pulses:
            await self._forward(self.cfg.movement.walk_speed_fraction, self.cfg.approach.forward_pulse_ms, note="approach")
            pulses += 1
            await asyncio.sleep(0.2)
        if self.state == STATE_APPROACH:
            self.state = STATE_INTERACT
            await self._interact_phase()
            self.state = STATE_RETURN
            await self._return_to_start()
            self.state = STATE_COMPLETE

    async def _interact_phase(self):
        logger.info("Interacting (waiting)...")
        await asyncio.sleep(self.cfg.interaction.wait_s)

    async def _return_to_start(self):
        logger.info("Returning to start via command log reversal")
        for cmd in reversed(self.command_log):
            if cmd.kind == 'forward':
                # invert forward by going backward same duration
                if self.cfg.simulation.enabled:
                    await asyncio.sleep(cmd.duration_ms/1000)
                else:
                    await self.dog.go_backward(cmd.speed, cmd.duration_ms)
            elif cmd.kind == 'turn_left':
                if self.cfg.simulation.enabled:
                    await asyncio.sleep(cmd.duration_ms/1000)
                else:
                    await self.dog.turn_right(cmd.speed, cmd.duration_ms)
            elif cmd.kind == 'turn_right':
                if self.cfg.simulation.enabled:
                    await asyncio.sleep(cmd.duration_ms/1000)
                else:
                    await self.dog.turn_left(cmd.speed, cmd.duration_ms)
        logger.info("Return sequence complete")
        if self.telemetry:
            self.telemetry.log(state=self.state, x=self.pose.x, y=self.pose.y, heading=self.pose.heading_rad,
                               cmd='return_complete', speed=0, duration_ms=0, note="")

    async def _stop_all(self):
        try:
            await self.dog.go_forward(0, 500)
        except Exception:
            pass
        if self.telemetry:
            self.telemetry.close()

import contextlib  # placed at end to avoid circular import issues
