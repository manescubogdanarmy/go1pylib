# Go1 Autonomous Vehicle Search & Approach Plan

## Objective
Develop a Python program using `go1pylib` that makes a Unitree Go1 EDU robot:
1. Systematically search a 400 m² area using a grid pattern.
2. Detect a target vehicle (e.g., based on vision or wireless beacon input).
3. Navigate toward the detected vehicle and stop at a safe standoff distance.
4. Indicate mission state via LEDs and log transitions.
5. Fail safely if the vehicle is lost or communications degrade.

This document is an engineering plan: architecture, modules, behaviors, data flows, safety, and incremental milestones.

---
## Assumptions & Constraints
- Area shape: Approx 20m × 20m (adjustable). Grid decomposition will parameterize width/height.
- Localization: Initially dead-reckoning (odometry via commanded gait timing) + optional future fusion (AprilTags, UWB, GPS if available). Baseline library does not expose full kinematics; we approximate distance traveled by command duration * nominal speed factor.
- Vehicle detection: Placeholder interface `IVehicleDetector` returning (confidence, bearing, distance_estimate_optional). Implementation options:
  - Vision YOLOv8 / YOLOv11 model (external process) sending detections over a local socket or MQTT.
  - Bluetooth/UWB RSSI gradient (if available hardware) for bearing triangulation.
  - Manual test stub (random detection after N seconds) for development.
- Obstacle avoidance: Reuse reactive avoidance from `examples/avoid_obstacles.py` (distance warnings front/left/right). During search: mild avoidance, during approach: stricter.
- Speeds kept conservative (0.2–0.4 normalized) for stability.
- Mission termination: Success (vehicle reached) or timeout.

---
## High-Level Architecture
```
main.py
 ├── MissionController
 │     ├── SearchPlanner (grid waypoint generator)
 │     ├── Navigator (low-level motion segment executor)
 │     ├── VehicleDetectorAdapter (pluggable backend)
 │     ├── AvoidanceModule (event-driven from go1_state_change)
 │     ├── StateEstimator (lightweight pose integration)
 │     └── EventBus / Callbacks
 └── go1pylib.Go1 (movement + mode + LEDs + state events)
```

### Core Components
1. MissionController
   - Finite State Machine (FSM): INIT → SEARCH → APPROACH → CONFIRM → SUCCESS / FAIL / ABORT.
2. SearchPlanner
   - Generates serpentine (lawnmower) path covering W×H area with lane spacing L (e.g., 2m lanes ⇒ 10 passes for 20m width).
3. Navigator
   - Converts waypoints into movement pulses using `go_forward`, `turn_left/right`, `go_left/right` as needed.
   - Time-based odometry accumulation (pose.x, pose.y, heading).
4. VehicleDetectorAdapter
   - `poll()` returns structured detection or None.
5. AvoidanceModule
   - Adapts logic from `CollisionAvoidance`: modifies immediate motion requests (stop/turn) if obstacle threshold triggered.
6. StateEstimator
   - Heading updated on turn commands (assumed instantaneous or over command duration).
   - Distance = forward_speed_norm * nominal_mps * (duration_ms / 1000). (Need parameter `nominal_mps`— empirically calibrate; start with 1.3 m/s at speed=1.0 for Go1 WALK.)
7. LED Strategy
   - INIT: Blue (0,0,255)
   - SEARCH: Green (0,255,0)
   - DETECT (transition): Yellow (255,200,0)
   - APPROACH: Cyan (0,255,255)
   - SUCCESS: Purple (180,0,255)
   - FAIL/ABORT: Red (255,0,0)

---
## Finite State Machine Details
| State | Entry Action | Loop Behavior | Exit Condition |
|-------|--------------|---------------|----------------|
| INIT | set_mode(WALK), LED Blue | Wait connectivity & warm-up | Robot ready |
| SEARCH | LED Green | Follow grid waypoints, monitor detector each cycle | Detection above confidence threshold |
| APPROACH | LED Cyan | Turn toward bearing, move forward bursts, refine heading | Distance < target_standoff OR detection lost > grace_period |
| CONFIRM | LED Yellow | Small forward micro-adjust, re-check detection | Confirmed N consecutive frames OR lost |
| SUCCESS | LED Purple | Stop, stand_down optional | Timeout for mission end |
| FAIL | LED Red | Stop, stand_down | Manual reset |
| ABORT | LED Red | Stop quickly | Manual reset |

---
## Search Pattern Generation
Parameters:
- width_m, height_m (defaults 20,20)
- lane_spacing_m (e.g., 2.0)
- forward_segment_m (derived from lane length)
Algorithm (serpentine):
1. For y = 0 .. height step lane_spacing: generate line from (0,y)→(width,y) if even index else (width,y)→(0,y).
2. Append small lateral move (lane shift) between passes except last.
3. Convert each segment into a sequence of (heading_target, distance_m) pairs.

Conversion to movement commands:
- Required heading difference ⇒ issue `turn_left/right` with duration = abs(delta_heading)/yaw_rate (estimate yaw_rate rad/s from empirical constant, e.g., 90° in 1s at speed=0.5 ⇒ 1.57 rad/s).
- Forward distance ⇒ `go_forward(speed, duration_ms)` with duration_ms = (distance_m / (speed * nominal_mps)) * 1000.

---
## Vehicle Detection Integration
Abstract Interface:
```python
dataclass VehicleDetection:
    confidence: float
    bearing_deg: float  # relative to robot forward (-180..180)
    est_distance_m: Optional[float] = None
```
Adapter Responsibilities:
- Listen to external process (socket, MQTT, file, stub).
- Provide smoothing: moving average of last K bearings.
- Provide grace window for temporary loss (e.g., 2s) before reverting to SEARCH.

Transition criteria:
- SEARCH→APPROACH: detection.confidence >= C_detect (e.g., 0.65) in at least M of last N polls.
- APPROACH→CONFIRM: est_distance_m <= standoff_distance (e.g., 1.5 m) or approached cumulative forward distance approximating target.
- CONFIRM→SUCCESS: detection persists stable for T_confirm seconds.
- APPROACH→SEARCH: lost for > grace_period.

---
## Motion & Odometry Parameters (Initial Defaults)
- nominal_forward_mps = 1.3 * speed_norm (speed_norm ≤ 0.4 for safety during search/approach ⇒ ~0.52 m/s).
- yaw_rate_rad_per_s at turn_speed=0.5 ≈ 1.6 rad/s (tune empirically). Duration_ms for heading change = (abs(delta_heading_rad)/yaw_rate) * 1000.
- lane_spacing_m = 2.0; width=20m → 10 passes; each pass 20m forward.
- Total nominal distance = 10 * 20m = 200m + lateral transitions (~9 * 2m = 18m) ≈ 218m path length.

---
## Safety & Failsafes
1. Obstacle avoidance preempts search/approach commands, injecting stop + turn pulses.
2. Max continuous forward command duration clamp (e.g., 3000 ms) to allow frequent re-evaluation.
3. Heartbeat: if no MQTT connectivity for > 2s, enter ABORT.
4. Watchdog on detection timestamp; stale detection ignored.
5. Emergency stop procedure: set all speeds zero, send movement command 500 ms, set LED red, optionally STAND_DOWN.

---
## Incremental Development Milestones
1. Skeleton modules + FSM logging (no real search movement yet). Outcome: transitions visible.
2. Implement grid planner + time-based odometry; dry-run (no robot) logging planned pose vs internal state.
3. Integrate movement commands with conservative speeds; test small (4m x 4m) grid.
4. Add avoidance reuse from `avoid_obstacles.py`; inject test obstacle states.
5. Implement stub `VehicleDetectorAdapter` (random detection) to validate transitions to APPROACH.
6. Implement bearing-based turning + staged approach pulses (approach in 1m increments).
7. Add confirmation logic + success termination.
8. Integrate real detector (vision or beacon); calibrate thresholds.
9. Tune parameters (speed, yaw_rate, confidence gating, lane spacing) in live environment.
10. Add telemetry export (JSON log) + mission summary.

---
## Module & File Layout Proposal
```
src/go1pylib/mission/
  __init__.py
  fsm.py                # MissionController & states
  planner.py            # SearchPlanner
  navigator.py          # Navigator & odometry
  detection.py          # VehicleDetection dataclass + adapters
  avoidance.py          # Wrapper around existing collision logic
  params.py             # Tunable constants
  utils.py              # Heading math etc.
examples/
  vehicle_search.py     # Entry script using mission package
```

---
## Key Pseudocode Snippets
### FSM Loop
```python
while running:
    now = monotonic()
    detection = detector.poll(now)
    mission.update_detection(detection)
    mission.tick(now)
    await asyncio.sleep(loop_dt)
```

### Waypoint Execution (Navigator)
```python
heading_error = wrap_angle(target_heading - pose.heading)
if abs(heading_error) > heading_tol:
    await turn_to_heading(heading_error)
await forward_distance(dist_m)
```

### Forward Distance Helper
```python
async def forward_distance(dist_m, speed=0.35):
    dur_ms = int((dist_m / (nominal_forward_mps * speed/1.0)) * 1000)
    dur_ms = min(dur_ms, MAX_PULSE_MS)
    await dog.go_forward(speed, dur_ms)
    pose.x += dist_m * cos(pose.heading)
    pose.y += dist_m * sin(pose.heading)
```

---
## Telemetry & Logging
- Structured JSON lines: timestamp, state, pose, last_detection, current_segment, battery (if available).
- Export file: `logs/mission_<ISO8601>.jsonl`.
- Optional real-time console table.

---
## Testing Strategy
1. Unit tests for planner path length and waypoint ordering.
2. Simulation harness that stubs `Go1` movement with immediate pose updates (no MQTT) for rapid iteration.
3. Fault injection: force obstacle triggers mid-waypoint; ensure recovery.
4. Detection simulation: scripted bearings causing APPROACH transitions.
5. Field test with reduced 4×4 m grid before full 20×20 m deployment.

---
## Parameter Tuning Checklist
| Parameter | Start | Adjust For |
|-----------|-------|------------|
| speed_search | 0.30 | Coverage speed vs stability |
| speed_approach | 0.25 | Precision near vehicle |
| lane_spacing_m | 2.0 | Coverage density |
| detection_confidence C_detect | 0.65 | False positives/negatives |
| detection_grace_s | 2.0 | Intermittent loss |
| standoff_distance_m | 1.5 | Safety buffer |
| yaw_rate_rad_s | 1.6 | Empirical calibration |
| max_forward_pulse_ms | 3000 | Replanning cadence |

---
## Open Questions / Future Enhancements
- Replace time-based odometry with fused IMU + visual odometry (e.g., ORB-SLAM2) integration.
- Multi-sensor detection fusion (vision + thermal + RFID). 
- Dynamic replanning to skip already-seen areas (coverage map occupancy grid).
- Return-to-start or autonomous docking on mission end.
- Remote operator override channel (web UI or joystick). 

---
## Next Implementation Steps (Immediate)
1. Create `mission` package scaffold and dataclasses.
2. Add `vehicle_search.py` example that initializes Go1, sets mode, runs MissionController.
3. Implement SearchPlanner and basic Navigator with logging only (no robot). 
4. Integrate real movement commands once logging path looks correct.

---
## Acceptance Criteria (MVP)
- Robot covers at least 90% of 20×20 m grid lanes (based on odometry log) when no detection occurs for full mission time limit.
- On simulated detection (injected) robot transitions to APPROACH within <1s.
- Robot reaches within standoff_distance ±0.5m of injected target position in simulation harness.
- No continuous movement command exceeds max_forward_pulse_ms.
- Safe abort (manual KeyboardInterrupt) stops motion and sets LED red reliably.

---
Prepared: 2025-09-10
