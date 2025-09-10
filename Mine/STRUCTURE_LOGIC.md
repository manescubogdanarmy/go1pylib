# Mine Module - Structure & Logic

## 1. Command Quick Reference (Most Used First)
| Purpose | Command |
|---------|---------|
| Autonomous 7×7m search (real robot) | `python Mine/main.py --config Mine/mine_config.yaml --auto-search --no-simulation` |
| Autonomous 7×7m search (simulation) | `python Mine/main.py --config Mine/mine_config.yaml --auto-search --simulation` |
| Manual camera + labeling (no movement) | `python Mine/main.py --config Mine/mine_config.yaml` |
| Force simulation on (override YAML) | `python Mine/main.py --config Mine/mine_config.yaml --simulation` |
| Force simulation off (override YAML) | `python Mine/main.py --config Mine/mine_config.yaml --no-simulation --auto-search` |
| Run unit tests | `pytest Mine/tests -q` |
| Install module extras | `pip install .[mine]` |

Keypress Summary (shown in GUI):
- `y` = label current detected circle as `mine`
- `n` = label as `not_mine`
- `s` = skip (no save)
- `q` = quit session / close labeling window

---
## 2. High-Level Concept
The Mine module provides an autonomous lawn‑mower (lane) search over a rectangular area while performing classical round object detection using OpenCV (Hough Circles). When a candidate circular object is found:
1. Mission pauses search state.
2. Frame + detections are presented to the operator GUI.
3. User labels detection (mine / not mine) — crops saved for future ML dataset building.
4. Search resumes until area coverage completes.

---
## 3. Folder Structure
```
Mine/
  main.py              # CLI entrypoint (manual vs auto modes)
  mission.py           # Autonomous search state machine
  detector.py          # Hough circle detection logic
  gui.py               # Labeling + visualization (OpenCV HighGUI)
  config.py            # YAML -> dataclasses (vision, area, movement, logging, simulation)
  mine_config.yaml     # Default configuration
  telemetry.py         # CSV telemetry logging utilities
  README.md            # User-facing quick usage guide
  STRUCTURE_LOGIC.md   # (This file) Architectural + logic reference
  tests/
    test_detector.py   # Basic smoke test for detector class
  dataset/
    mine/              # Labeled positive crops
    not_mine/          # Labeled negative crops
  logs/                # Telemetry CSV files (sessions & auto-search)
```

---
## 4. Runtime Modes
| Mode | Trigger | Movement | Vision | GUI | Label Storage |
|------|---------|----------|--------|-----|---------------|
| Manual | `main.py` (no `--auto-search`) | None | Continuous | Yes | On detection frames only |
| Auto Search | `--auto-search` | Lane pulses + turns | Pulse boundary checks | Yes | On detection frames |
| Simulation | YAML `simulation.enabled=true` or `--simulation` | Sleeps instead of commands | Same | Yes | Same |

`--no-simulation` overrides YAML to force real movement.

---
## 5. Configuration Model (`mine_config.yaml`)
```yaml
vision:
  enabled: true
  camera_index: 0
  blur_kernel: 5
  canny_low: 50
  canny_high: 150
  dp: 1.2
  min_dist: 40
  param1: 120
  param2: 30
  min_radius: 10
  max_radius: 160
  save_dir: Mine/dataset
logging:
  level: INFO
  telemetry: true
  telemetry_dir: Mine/logs
simulation:
  enabled: false        # Set true to suppress real movement
area:
  width_m: 7.0          # Search rectangle width
  height_m: 7.0         # Search rectangle height
  lane_width_m: 2.0
movement:
  walk_speed_fraction: 0.25
  forward_pulse_m: 1.0
  turn_90_ms: 1500
  max_search_speed_mps: 1.2
```

---
## 6. State Machine (Auto Mode)
States: `INIT -> SEARCH -> (LABEL)* -> COMPLETE`

Textual Flow:
```
INIT: initialize dog mode (WALK) & generate lanes
  ↓
SEARCH: iterate lanes
  ├─ forward pulses → detection? yes → LABEL
  └─ end lanes → COMPLETE
LABEL: submit frame to GUI → wait (timeout or label) → back to SEARCH
COMPLETE: mission done
```
Unlike SnD, there is no RETURN or APPROACH—mission ends after full coverage.

---
## 7. Lane Traversal Logic
- Lanes generated using `SnD.lane_planner.generate_lanes(width, height, lane_width)`.
- Zig‑zag pattern: vertical passes with 0.5 m lateral transition using two right turns.
- Pulse control:
  - Distance per pulse = `movement.forward_pulse_m` (converted via speed fraction to duration).
  - Duration (ms) = `(pulse_m / (walk_speed_fraction * max_search_speed_mps)) * 1000`.

---
## 8. Detection Pipeline (`detector.py`)
Steps per pulse:
1. Capture frame (`VideoCapture.read`).
2. Convert to grayscale.
3. Optional Gaussian blur (`blur_kernel`).
4. Edge map (`Canny`).
5. HoughCircles with tunable parameters (`dp`, `min_dist`, `param1`, `param2`, radius bounds).
6. Each circle → `CircleDetection(ts, x, y, r, strength=r)` (strength currently radius heuristic).

Future Improvements:
- Add adaptive histogram equalization.
- Use HSV mask for selective color filtering (painted objects).
- Learn-based replacement (YOLO fine-tune on saved dataset).

---
## 9. GUI (`gui.py`)
- Runs a background thread consuming submitted frames.
- Draws circles; first detection is active target for labeling.
- Key overlay always shown: `Keys: y=mine n=not_mine s=skip q=quit`.
- On label: frame crop (square bounding radius) saved under `mine/` or `not_mine/`.
- Non-blocking preview (mission loop also injects preview frames when idle/detection-free).

Enhancement Ideas:
- Iterate through all detections (Left/Right arrow to cycle).
- Confidence/radius-driven ordering.
- Add full-frame save toggle for dataset augmentation.

---
## 10. Telemetry (`telemetry.py` & Auto Mode)
Auto-search CSV columns:
`ts,state,x,y,heading,cmd,speed,duration_ms,detections`

Manual mode telemetry: `ts,num_detections,latency_ms`.

Use Example:
```python
import pandas as pd, glob
latest = sorted(glob.glob('Mine/logs/mine_auto_*.csv'))[-1]
df = pd.read_csv(latest)
print(df['cmd'].value_counts())
```

---
## 11. Simulation vs Real Movement
| Aspect | Simulation | Real |
|--------|------------|------|
| Pulse Execution | `asyncio.sleep()` | MQTT movement command | 
| Timing Accuracy | Idealized | Subject to drift / network latency |
| Safety Risk | None | Must ensure clear test area |
| Logging | Same | Same |

Switching: CLI flags override YAML; precedence `--no-simulation` > `--simulation` > YAML.

---
## 12. Entry Points Summary
| File | Role |
|------|------|
| `main.py` | CLI parsing, dispatch manual vs auto mode |
| `mission.py` | Autonomous mission controller (state machine) |
| `detector.py` | Circle detection routines |
| `gui.py` | User labeling UI |
| `config.py` | Typed config loader |
| `telemetry.py` | CSV logging helpers |

---
## 13. Error Handling & Diagnostics
Current mitigations:
- Connection status logging before search start (mission start).
- Simulation logs when pulses are skipped.
- Frame preview even when no detections (visual heartbeat).

Suggested additions (future):
- Retry camera open with exponential backoff.
- FPS / latency overlay stats.
- Watchdog: if no frames for N seconds → abort or restart camera.

---
## 14. Extension Points
| Goal | Approach |
|------|----------|
| Multi-object labeling | Iterate detection list; index overlay + next/prev keys |
| Return-to-start path | Reuse command reversal from SnD (`CommandRecord` already stored) |
| Confidence scoring | Replace `strength=radius` with accumulator or edge contrast |
| ML integration | Export dataset + train YOLO model → import model path into new detector class |
| Distance estimation | Approximate via known object size vs pixel radius |
| Web UI | Replace HighGUI with websocket server streaming JPEG frames |

---
## 15. Known Limitations
- No reverse path / end-of-mission reposition.
- Single detection labeled per frame (first circle only).
- No dynamic lane adaptation (e.g., skip already covered region if operator halts mid-lane).
- HoughCircles sensitive to lighting and contrast.

---
## 16. Quick Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| No GUI window | Headless environment | Run with display / enable X forwarding |
| No movement (auto) | Simulation still enabled | Use `--no-simulation` or set config false |
| Too many false positives | `param2` too low | Increase `param2` or raise `min_radius` |
| Missed small objects | `min_radius` too high | Lower `min_radius` |
| Laggy GUI | High resolution camera | Reduce camera resolution or add frame skip |

---
## 17. Minimal Control Flow (Auto Mode Pseudocode)
```python
init()
set_mode(WALK)
lanes = generate_lanes()
for lane in lanes:
    while lane.remaining > 0:
        forward_pulse()
        frame, dets = detect()
        if dets:
            label_phase(frame, dets)
    lane_transition()
complete()
```

---
## 18. Data Artifacts
| Artifact | Location | Description |
|----------|----------|-------------|
| Telemetry CSV | `Mine/logs/` | Movement & detection metadata |
| Crops (mine) | `Mine/dataset/mine/` | Positive labeled examples |
| Crops (not mine) | `Mine/dataset/not_mine/` | Negative examples |

---
## 19. Maintenance Checklist
- Verify `turn_90_ms` quarterly (battery wear affects timing).
- Cull duplicate crops (hash-based dedupe) before ML training.
- Archive telemetry + dataset snapshots with semantic version tags.
- Log OpenCV + Python versions for reproducibility.

---
## 20. Future Roadmap Ideas
1. Add asynchronous detection (separate task) to overlap motion & vision.
2. Integrate person avoidance while searching (reuse SnD collision logic).
3. Provide REST endpoint for remote supervision.
4. Bundle dataset export script (manifest JSON with metadata per crop).
5. Optional GPU acceleration for higher resolution circle detection.

---
*End of STRUCTURE_LOGIC.md*
