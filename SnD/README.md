# Search & Detect (SnD) Mission Guide

Comprehensive instructions to configure, run, test, calibrate, and troubleshoot the Human Search & Approach mission for the Unitree Go1 using `go1pylib`.

---
## 1. Overview
The SnD module autonomously searches a rectangular area using a lawn‑mower (grid) pattern. It performs real‑time person detection (YOLO), approaches the detected human, waits 15 seconds, then returns to the start using command reversal. Includes telemetry logging, collision avoidance gating (distance warnings), and a fake detection test hook.

Mission State Flow:
`INIT -> SEARCH -> (APPROACH -> INTERACT -> RETURN) -> COMPLETE` (or `FAILSAFE` on errors)

---
## 2. Folder Structure
```
SnD/
  README.md                (this file)
  search_config.yaml       (mission configuration)
  main.py                  (entrypoint)
  controller.py            (state machine)
  config.py                (YAML -> dataclasses)
  lane_planner.py          (lane generation utilities)
  pose.py                  (dead-reckoning pose helpers)
  vision.py                (YOLO detection with debounce)
  telemetry.py             (CSV logger)
  tests/                   (basic tests)
  logs/                    (created at runtime for telemetry)
```

---
## 3. Requirements
Core library already installed via editable install:
```
pip install -e .
```
Search dependencies (extras declared in `setup.cfg`):
```
pip install .[search]
```
If bracket expansion fails (PowerShell quoting), install explicitly:
```
pip install ultralytics opencv-python pyyaml numpy filterpy scipy
```

> NOTE: Ultralytics downloads the model (e.g. `yolov8n.pt`) on first run.

---
## 4. Configuration (`search_config.yaml`)
Key sections:
| Section | Key Fields | Purpose |
|---------|------------|---------|
| area | width_m, height_m, lane_width_m | Coverage geometry |
| movement | walk_speed_fraction, max_search_speed_mps, forward_pulse_m, turn_90_ms | Motion timing & calibration |
| vision | enabled, model, conf_threshold, debounce/min_positive_frames | Person detection behavior |
| approach | center_threshold_pct, forward_pulse_ms, stop_distance_m | Approach behavior (range placeholder) |
| timeouts | lost_target_s | Drop back to SEARCH if target lost |
| interaction | wait_s | Time to wait near human |
| return | strategy | Currently `reverse_log` only |
| safety | battery thresholds, enable_collision_adapter | Failsafe settings |
| logging | level, telemetry, telemetry_dir | Runtime logging & CSV output |
| simulation | enabled | Disable physical movement (timed sleeps only) |

Edit values to scale area or adjust performance. For initial field tests reduce area to something like 4m × 4m.

---
## 5. Quick Start (Simulation)
```
python SnD/main.py --simulation
```
Expected: executes lanes until completion (no detection) then returns and exits.

### Inject a Fake Detection (Simulation)
Add after controller creation in `main.py`:
```python
controller.fake_detection = True
```
Re-run. You’ll see state transition to APPROACH, then INTERACT (15s), RETURN, COMPLETE.
Remove the line after verification.

---
## 6. Quick Start (Real Robot)
1. Power on Go1; ensure network / MQTT connectivity used by `go1pylib`.
2. Verify basic movement example still works (`examples/move_forward.py`).
3. (Optional) Reduce area in `search_config.yaml` for first trial.
4. Run:
```
python SnD/main.py
```
5. Observe logs; confirm state enters `SEARCH` and forward pulses occur.
6. Present a person in front of camera inside FOV.
7. On detection: logs show transition to APPROACH -> INTERACT -> RETURN.

> If detection never triggers, open a terminal and test YOLO directly:
```python
from ultralytics import YOLO
m = YOLO('yolov8n.pt')
print('Loaded model classes:', m.names)
```

---
## 7. Telemetry
CSV file output created under `SnD/logs/` with filename `session_<UTCSTAMP>.csv`.
Columns: `ts,state,x,y,heading,cmd,speed,duration_ms,note`.
Example analysis:
```python
import pandas as pd, glob
latest = sorted(glob.glob('SnD/logs/session_*.csv'))[-1]
df = pd.read_csv(latest)
print(df.state.value_counts())
```
Use for calibration (compare expected vs executed pulses, heading drift).

---
## 8. Calibration Procedures
### Forward Distance Calibration
1. Set small test: `forward_pulse_m: 1.0`, speed fraction 0.3.
2. Measure actual distance traveled for a single pulse (tape measure).
3. Compute effective speed: `measured_distance / (duration_ms / 1000)`.
4. Update `max_search_speed_mps` to match measured speed.

### Turn Duration Calibration
1. Run a square using existing `square.py` or modify mission to execute four 90° turns.
2. Measure heading error after full cycle.
3. Adjust `turn_90_ms` (+/- 50 ms) until error minimized.

### Lane Width Validation
Ensure detection FOV covers gap between adjacent lanes. If gaps appear, reduce `lane_width_m`.

---
## 9. Collision Avoidance Integration
Enabled by `safety.enable_collision_adapter: true`.
- If distance warnings (front < 0.75, left/right < 0.5) are triggered, forward pulses are skipped.
- To adjust thresholds: edit code in `controller.py` inside `on_state` handler (search for `collision_block`). Future improvement: move thresholds into config.

---
## 10. Person Detection Tuning
| Parameter | Effect | Typical Range |
|-----------|-------|---------------|
| `vision.model` | Accuracy vs speed | `yolov8n.pt` (fast), `yolov8s.pt` (better) |
| `conf_threshold` | Min confidence per frame | 0.45 – 0.6 |
| `debounce_frames` | Frame window | 3 – 8 |
| `min_positive_frames` | Frames required within window | 2 – 5 |

If false positives: raise `conf_threshold` or increase `min_positive_frames`.
If missed detections: lower thresholds or use a larger model.

---
## 11. Unit Tests
Run basic tests:
```
pytest SnD/tests -q
```
Current tests cover lane generation and pose updates. Extend with:
- Command reversal integrity
- Telemetry file creation
- Synthetic detection flow (mock detector)

---
## 12. Fake Detection Hook (Without Camera)
When `controller.fake_detection = True` before mission start, a single synthetic detection event is injected. Good for validating full state cycle indoors or without camera access.

---
## 13. Simulation vs Real Mode
| Aspect | Simulation | Real |
|--------|-----------|------|
| Movement | Timed sleeps | Sends MQTT motion commands |
| Telemetry | Yes | Yes |
| Vision | Still attempts detection (if enabled) | Live camera |
| Safety | No physical risk | Ensure clear test area |

Switch using CLI flag `--simulation` or set `simulation.enabled: true` in YAML.

---
## 14. Safety Checklist (Real Runs)
- Battery ≥ 30%
- Flat, obstacle‑free area
- Emergency stop accessible (power or manual remote)
- Initial area scaled down (start with 4m × 4m)
- Cable slack or accessories secured
- Only one operator inside test boundary until behavior validated

---
## 15. Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| "No detection" | Camera index wrong | Change `camera_index` in config or test webcam with OpenCV snippet |
| Immediate FAILSAFE | Low battery threshold hit | Charge robot / lower threshold temporarily (not recommended) |
| Stuck in SEARCH but not moving | Collision block active | Check distance warnings; raise thresholds or clear space |
| Return path inaccurate | Dead-reckoning drift | Shorten mission, calibrate speed/turns, add periodic re-alignment |
| YOLO slow | Model too large / CPU only | Use `yolov8n.pt`, reduce frame rate (sleep in vision loop) |
| Telemetry missing | Logging disabled | Ensure `logging.telemetry: true` |

---
## 16. Extending
Planned improvements:
- Infer distance from bounding box height for early stop.
- Waypoint-based return (less drift).
- Configurable collision thresholds in YAML.
- CLI flag for fake detection (instead of code edit).
- CSV + JSON mission summary (success metrics).

---
## 17. Example End-to-End Workflow
1. Edit `SnD/search_config.yaml` to: width=6, height=6, lane_width=2.
2. Run simulation: `python SnD/main.py --simulation`.
3. Insert fake detection and re-run; verify state transitions.
4. Calibrate turn: Adjust `turn_90_ms` while observing orientation drift.
5. Remove fake detection; run real mission with camera.
6. Present a person; monitor telemetry & logs.
7. Inspect latest CSV for coverage and return sequence.

---
## 18. Command Reference
| Command | Purpose |
|---------|---------|
| `python SnD/main.py --simulation` | Full mission dry run |
| `python SnD/main.py` | Real mission |
| `pytest SnD/tests -q` | Run tests |
| `pip install .[search]` | Install vision & search deps |

---
## 19. Known Limitations
- No real range estimation yet (approach pulses capped).
- Drift accumulates over long searches (no SLAM integration).
- Collision avoidance is binary and simple.
- Return path does not adapt to skipped pulses (still functional, but may misplace final position if drift high).

---
## 20. Support / Next Steps
If you’d like automation for distance estimation or improved return strategy, create an issue or request an enhancement. For immediate tweaks, adjust YAML then re-run.

---
**End of Guide**
