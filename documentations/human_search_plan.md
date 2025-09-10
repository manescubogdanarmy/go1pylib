## Human Search & Approach Plan for Unitree Go1 EDU

### 1. Objective
Develop a Python program (building on `go1pylib`) that makes the Unitree Go1 EDU:
1. Systematically search a 400 m² area (e.g. 20m x 20m) using a grid / lawn‑mower (boustrouphedon) pattern.
2. Perform real‑time human detection via onboard or external RGB (and optionally depth) camera.
3. When a human is detected with sufficient confidence:
	 - Break out of search.
	 - Safely approach the person until within a configurable proximity.
	 - Wait (idle) for 15 seconds (interaction window).
	 - Return to the original start point.
4. Provide LEDs / logging / optional audio feedback for state transitions.

### 2. Assumptions & Constraints
| Topic | Assumption / Strategy |
|-------|-----------------------|
| Localization | No high‑precision SLAM exposed in current repo; we approximate pose using dead‑reckoning (commanded speed × time) + optional IMU/state once available from `go1_state_change`. Future: integrate VSLAM (ORB-SLAM2, RTAB-Map, or Unitree SDK). |
| Area | Rectangular ~400 m² (default 20m x 20m). Dimensions configurable. |
| Camera | USB / Realsense / OAK-D / built-in stream accessible via OpenCV (`cv2.VideoCapture`). |
| Human detection | YOLO (Ultralytics) or alternative (MediaPipe / OpenPose). Start with YOLO for simplicity + speed on GPU/CPU. |
| Network | Robot + control workstation on same LAN. MQTT already handled by `go1pylib`. |
| Safety | Speeds kept conservative (≤0.35). Immediate stop if distance warning trigger (reuse collision avoidance logic). |
| Return path | Reverse executed movement commands (command log) OR follow stored waypoints at lane boundaries. |
| Timing | Async tasks: movement planner, vision loop, state monitor. |
| Power | Ensure battery > threshold (e.g. 30%) before initiating full search. |

### 3. High-Level Architecture
```
+-------------------------+            +------------------------+
|   Vision Task (YOLO)    |  detects   |  State Machine / Core  |
|  - Frame capture        +----------->|  SEARCH / APPROACH /   |
|  - Inference            |  events    |  INTERACT / RETURN     |
|  - Human bounding boxes |            +-----------+------------+
|  - Range estimate (opt) |                        |
 +-----------+-------------+                        v
						 |                               +-------------+
						 | pose / est. range              | Motion     |
						 v                                | Controller |
+-------------------------+                   | (go1pylib) |
|  Localization / Path    |<------------------+-------------+
|  - Dead reckoning       | telemetry       Movement primitives
|  - Waypoints grid       |
|  - Command log          |
 +------------------------+
```

### 4. Required / Recommended Python Packages
Core (already present / standard):
- `go1pylib` (this repo, installed editable: `pip install -e .`)
- `asyncio`, `logging`, `time`, `math`, `dataclasses` (stdlib)

Vision / Detection:
- `ultralytics` (YOLOv8/YOLOv11) or `onnxruntime` + exported model for lighter runtime.
- `opencv-python` (camera capture & image ops)
- `numpy`

Optional Depth / Range:
- `pyrealsense2` (Intel RealSense) OR `depthai` (Luxonis OAK-D).

Localization & Filtering (future / optional):
- `filterpy` (Kalman filtering)
- `scipy`

Configuration & Dev Quality (optional):
- `pydantic` (structured config)
- `loguru` (richer logging) / keep stdlib for simplicity.

Performance (optional enhancements):
- `torch` (installed automatically with `ultralytics` for training/inference)
- `onnxruntime-gpu` (if using exported ONNX model)

Testing / Tooling:
- `pytest`
- `mypy` (static checks if you extend types)

Example install command set:
```bash
pip install ultralytics opencv-python numpy filterpy scipy pydantic loguru
# If using RealSense:
pip install pyrealsense2
# (Optional) for ONNX runtime
pip install onnxruntime
```

### 5. State Machine Definition
| State | Description | Entry Trigger | Exit Trigger |
|-------|-------------|---------------|--------------|
| INIT | Setup, connectivity, battery check | Program start | Connected & ready |
| SEARCH | Execute grid lanes, monitor vision | INIT complete / return incomplete | Human detected |
| APPROACH | Navigate toward detected human | Human detection event | Within proximity or lost target (timeout) |
| INTERACT | Wait 15s near human | Reached proximity | Timer elapsed |
| RETURN | Navigate back to start (reverse log) | Interaction done | Start reached |
| COMPLETE | Mission end | Return success | Shutdown |
| FAILSAFE | Emergency stop / low battery / collision | Any error or hazard | Manual reset |

### 6. Grid / Coverage Strategy
We treat search area as rectangle `width x height` (default 20m x 20m). Use lawn‑mower pattern with lane spacing = `lane_width` chosen so camera + detection FOV ensures coverage overlap.

Formula:
- Number of lanes `L = ceil(width / lane_width)`
- Each lane traversal length = `height`
- Total path length ≈ `L * height + (L-1) * turn_spacing` (turn overhead small).

Example values:
- Camera horizontal FOV ~70°; reliable detection width at 5m distance ≈ 2 * 5 * tan(35°) ≈ 7 m. To ensure overlap, choose `lane_width = 3 m`.
- For width=20m ⇒ `L = ceil(20 / 3) = 7` lanes.

Movement Implementation (dead reckoning):
- Convert desired linear distance to movement duration: `duration_ms = (distance_m / (speed_mps)) * 1000`.
- Speed mapping: If `speed` parameter (0–1) corresponds linearly to m/s max (e.g. assume max safe walking ~1.0 m/s for search), then `speed_mps = speed * max_search_speed` (tune by experiment).

Turns:
- Calibrate 90° turn duration once: run `turn_right(speed=0.3, duration_ms=? )` until actual 90° observed; store constant (e.g. 1500 ms, as example from `square.py`).

### 7. Human Detection Pipeline
1. Acquire frame (OpenCV): `ret, frame = cap.read()`.
2. Run YOLO model: `results = model(frame)`.
3. Filter for class `person` with confidence ≥ `conf_thresh` (e.g. 0.5–0.6).
4. Aggregate across N frames (debounce) to reduce false positives (e.g., require K≥3 positives in last M=5 frames).
5. Estimate range: methods (choose one):
	 - Depth pixel (if depth camera) average inside bounding box center.
	 - Geometric approximation from bounding box height vs known human height.
6. Publish event to core: `on_human_detected(confidence, range, bbox)`.
7. Maintain last seen timestamp; if lost > `lost_timeout` during APPROACH revert to SEARCH (optionally resume nearest lane).

### 8. Approach Logic
Inputs: `range_estimate`, `bbox_center`.
Steps:
1. Align heading: if center_x deviates > `center_threshold` (e.g. 5% frame width), issue small `turn_left/right` pulse (closed-loop alignment).
2. Move forward pulses (e.g. 0.3 speed, 500–800 ms) while `range_estimate > stop_distance` (e.g. 2.0 m). If no reliable range, limit number of pulses with fallback stop.
3. Once within proximity, set LED (blue), transition to INTERACT.

### 9. Interaction Phase
1. Set LED color (e.g. yellow) or blink pattern.
2. `await asyncio.sleep(15)`.
3. Log presence; optionally record video snippet.

### 10. Return Strategy
Approach A (Baseline – Command Log Reversal):
- During SEARCH & APPROACH, append each movement command: `(type, speed, duration_ms)`.
- To return: iterate reversed list, invert semantics:
	- forward ⇒ backward (same speed/duration)
	- turn_left ⇒ turn_right (same duration) etc.
Pros: Simple; Cons: Accumulated drift.

Approach B (Lane Waypoints):
- Store start of each lane as `(x, y, heading)` (dead-reckoned).
- On RETURN: plan path with straight segments to start (A* over coarse grid or direct Manhattan path) using stored coordinates.

Approach C (Future – SLAM):
- Use onboard SLAM to localize globally; send goal to start coordinate.

We implement Approach A initially; optionally add B if drift unacceptable.

### 11. Dead Reckoning Pose Estimation
Maintain internal pose `(x, y, heading)`:
```
heading += turn_rate * dt   # approximate from known 90° turn pulses
x += cos(heading) * v * dt
y += sin(heading) * v * dt
```
Where `v = speed_mps` derived from commanded `speed` fraction. Calibrate effective `speed_mps` empirically (log actual time vs distance). Keep drift metrics.

### 12. Core Configuration Parameters (Example)
```yaml
area:
	width_m: 20.0
	height_m: 20.0
	lane_width_m: 3.0
movement:
	walk_speed_fraction: 0.3
	max_search_speed_mps: 1.0
	forward_pulse_m: 1.0
	turn_90_ms: 1500
vision:
	model: yolov8n.pt
	conf_threshold: 0.55
	debounce_frames: 5
	min_positive_frames: 3
approach:
	center_threshold_pct: 5
	forward_pulse_ms: 600
	stop_distance_m: 2.0
timeouts:
	lost_target_s: 5
interaction:
	wait_s: 15
return:
	strategy: reverse_log
```

### 13. Pseudocode Skeleton
```python
class HumanSearchController:
		def __init__(self, dog: Go1, config):
				self.dog = dog
				self.cfg = config
				self.state = 'INIT'
				self.command_log = []
				self.pose = Pose()
				self.human_detection = None

		async def run(self):
				await self._wait_connection()
				self.state = 'SEARCH'
				search_task = asyncio.create_task(self._search_loop())
				vision_task = asyncio.create_task(self._vision_loop())
				monitor_task = asyncio.create_task(self._monitor_state())
				await asyncio.gather(search_task, vision_task, monitor_task)

		async def _search_loop(self):
				for lane in self._lane_plan():
						if self.state != 'SEARCH':
								break
						await self._traverse_lane(lane)
				if self.state == 'SEARCH':
						# Completed without detection
						self.state = 'RETURN'
						await self._return_to_start()

		async def _vision_loop(self):
				cap = cv2.VideoCapture(0)
				model = YOLO(self.cfg.vision.model)
				while self.state not in ('COMPLETE', 'FAIL'):            
						ret, frame = cap.read()
						if not ret: continue
						result = model(frame)[0]
						person = self._extract_person(result)
						if person and self.state == 'SEARCH':
								if self._debounce_positive(person):
										self.human_detection = person
										self.state = 'APPROACH'
										await self._approach_person()
						await asyncio.sleep(0)

		async def _approach_person(self):
				while self.state == 'APPROACH':
						if self._close_enough():
								self.state = 'INTERACT'
								await self._interact()
								self.state = 'RETURN'
								await self._return_to_start()
								self.state = 'COMPLETE'
								break
						await self._alignment_and_forward_pulse()

		async def _return_to_start(self):
				for cmd in reversed(self.command_log):
						await self._execute_inverse(cmd)
```

### 14. Integration with Existing `go1pylib` Primitives
Use the provided async methods:
- `go_forward(speed, duration_ms)` – primary linear motion.
- `turn_left(speed, duration_ms)` / `turn_right(...)` – lane transitions & heading alignment.
- `set_mode(Go1Mode.WALK)` at start, `STAND_DOWN` at completion.
- LED feedback: search=green, approach=blue, interact=yellow, return=cyan, error=red.

### 15. Safety & Failsafes
| Risk | Mitigation |
|------|------------|
| Obstacle collision | Integrate existing collision avoidance handler; abort forward pulses if warning threshold triggered. |
| Human too close | Stop earlier (stop_distance_m) and do not nudge. |
| Lost connection | Transition to FAILSAFE, stop movement. |
| Battery low mid-search | Abort and return immediately. |
| Vision false positive | Debounce + confidence threshold + multi-frame persistence. |
| Dead-reckoning drift | Periodic re-alignment using known lane heading; log drift for later SLAM integration. |

### 16. Testing Strategy
1. Unit tests for: lane generation, pose updates, command log reversal.
2. Simulation/dry-run mode: Replace movement calls with pose updates & timestamps only.
3. Vision mock: Feed prerecorded video with a human appearing mid-run; ensure state transitions.
4. Field calibration: measure actual distance traveled for a fixed `duration_ms` to refine speed mapping constant.
5. Turn calibration: adjust `turn_90_ms` until square test returns near start (error ≤ tolerance).

### 17. Incremental Implementation Roadmap
1. Lane planner + dead-reckoning (no vision) – verify coverage path & return reversal.
2. Add command log + reversal reliability test.
3. Integrate vision loop with mock frames.
4. Real camera integration & YOLO model inference.
5. Approach tuning (centering thresholds, pulses).
6. Collision avoidance merge (shared stop flag arbitration).
7. Configuration externalization (YAML / JSON).
8. Add metrics & logging export (CSV of pose, detections, battery). 

### 18. Future Enhancements
- Replace dead-reckoning with fused IMU + VSLAM (e.g., ORB-SLAM2 or RTAB-Map) for precise return.
- Dynamic replanning around blocked lanes.
- Multi-human detection ranking (choose closest / stable target).
- Audio output or two-way communication on interaction.
- Cloud dashboard for mission telemetry.

### 19. Example Minimal Movement / Lane Generator (Conceptual)
```python
def generate_lanes(width_m, height_m, lane_width_m):
		lanes = []  # Each lane: (start_x, start_y, end_x, end_y)
		x = 0.0
		direction = 1  # 1: forward along +y, -1: reverse
		while x < width_m - 1e-6:
				lanes.append((x, 0 if direction == 1 else height_m, x, height_m if direction == 1 else 0))
				x += lane_width_m
				direction *= -1
		return lanes
```

### 20. Acceptance Criteria
- Covers configured area within ±10% path length estimate.
- Detects a clearly visible person (standing) at ≤10m with ≥90% reliability (test dataset) using chosen model.
- Stops within ≤0.5 m overshoot of target stop distance.
- Returns to within ≤2 m of starting location using baseline reversal (improve later with SLAM).
- Clean, logged state transitions; no unhandled exceptions over ≥15 min trial.

### 21. Next Steps (Actionable)
1. Create `search_config.yaml` with parameters (see Section 12).
2. Implement lane & command logging module.
3. Add vision module skeleton with dependency injection for model.
4. Integrate with `go1pylib` movement primitives asynchronously.
5. Field calibrate movement + turn constants.

---
This document will evolve as localization and perception capabilities expand. Update after first field trial with empirical drift, detection latency, and energy consumption metrics.

