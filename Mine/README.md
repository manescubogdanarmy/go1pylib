# Mine (Round Object Detection & Labeling)

This module parallels the structure of `SnD` but focuses on detecting generic round objects (e.g., disks, manhole covers, mock mines) using classical computer vision (Hough Circles) and providing a lightweight human-in-the-loop labeling interface. Collected samples are organized for future ML training.

## Features
- Real-time circle / round object detection via OpenCV HoughCircles
- Configurable preprocessing (blur & Canny) and circle parameters
- Interactive GUI (OpenCV window):
  - Shows detections with overlays
  - Press `y` to mark first highlighted detection as correct (mine)
  - Press `n` to mark as incorrect
  - Press `s` to skip frame
  - Press `q` to quit session
- Automatic cropping & saving of labeled detections into:
  - `Mine/dataset/mine/`
  - `Mine/dataset/not_mine/`
- Telemetry CSV with detection latency & counts
- (Optional) Autonomous lawn‑mower style search (`--auto-search`) similar to SnD using lane traversal + pause-on-detection labeling
- YAML configuration similar style to `SnD`

## Quick Start
Install dependencies (if not already):
```
pip install .[mine]
```
Run (manual detection loop):
```
python Mine/main.py --config Mine/mine_config.yaml
```

Autonomous search mode (robot movement with simulated or real pulses depending on config):
```
python Mine/main.py --config Mine/mine_config.yaml --auto-search
```
Press `q` in the OpenCV window to exit.

## Configuration (`mine_config.yaml`)
| Section | Key | Purpose |
|---------|-----|---------|
| vision | camera_index | Webcam index (0 default) |
| vision | blur_kernel | Gaussian blur kernel size (odd) |
| vision | canny_low/high | Edge thresholds |
| vision | dp | Inverse accumulator resolution (Hough) |
| vision | min_dist | Minimum distance between circle centers |
| vision | param1 | Upper threshold for internal Canny used by Hough |
| vision | param2 | Accumulator threshold (smaller -> more false positives) |
| vision | min_radius/max_radius | Radius bounds |
| vision | save_dir | Root directory for captured crops |
| area | width_m/height_m | Search rectangle dimensions |
| area | lane_width_m | Spacing between vertical lanes |
| movement | walk_speed_fraction | Fraction of max speed for pulses |
| movement | forward_pulse_m | Forward segment length per pulse |
| movement | turn_90_ms | Duration to produce ~90° turn |
| movement | max_search_speed_mps | Calibrated max speed estimate |
| logging | telemetry | Enable CSV logging |
| simulation | enabled | Skip physical movement (timed sleeps) |

## Telemetry
CSV written to `Mine/logs/mine_session_<UTCSTAMP>.csv` with columns:
`ts,num_detections,latency_ms`

## Extending
- Add color filtering (HSV mask) before Hough to focus on painted objects
- Integrate a learned detector (YOLO fine-tune) using saved dataset
- Multi-object per frame labeling (extend GUI to iterate each detection)
- Persist raw full frames for augmentation pipelines

## Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| No window appears | Headless environment | Run locally with display / use X forwarding |
| Many false circles | param2 too low | Increase `param2`, raise `min_radius` |
| Missed small objects | min_radius too high | Lower `min_radius` |
| Blurry / noisy | Poor lighting | Increase blur, adjust exposure, add lighting |

## License
Follows root project (MIT).
