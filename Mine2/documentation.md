# Mine2 Documentation (Deep Architecture)

## Goals
- Observe up to 5 camera feeds from Unitree Go1 EDU (RTSP/UDP or device indices)
- Display all feeds in a paged 2×2 grid (scroll to see all)
- Hough circle detection per stream with overlay + console logging
- Passive: no robot commands (operator uses remote); non-blocking streams
- Save detection crops into `unsorted/<camera_name>/` for later curation

## Config (`Mine2/mine2_config.yaml`)
```yaml
cameras:
  - { name: front_left,  uri: "rtsp://<robot-ip>/front_left",  enabled: true }
  - { name: front_right, uri: "rtsp://<robot-ip>/front_right", enabled: true }
  - { name: side_left,   uri: "rtsp://<robot-ip>/side_left",   enabled: true }
  - { name: side_right,  uri: "rtsp://<robot-ip>/side_right",  enabled: true }
  - { name: rear,        uri: "rtsp://<robot-ip>/rear",        enabled: true }
vision:
  blur_kernel: 5
  canny_low: 50
  canny_high: 150
  dp: 1.2
  min_dist: 40
  param1: 120
  param2: 30
  min_radius: 10
  max_radius: 160
dataset:
  root: Mine2/dataset
  mine_dir: Mine2/dataset/mine
  not_mine_dir: Mine2/dataset/not_mine
  unsorted_dir: Mine2/dataset/unsorted
logging_level: INFO
```

## Components
- `streams.py` – CamWorker: one thread per camera, continuously captures frames and keeps only latest frame in a 1-slot queue (non-blocking semantics). Auto-retries on read failure.
- `detector.py` – HoughDetector: configurable Hough circle detection; returns DetectionEvents. Helper `save_crop` writes detection crops.
- `gui.py` – MultiFeedGUI: renders up to 4 feeds (2×2) per page; overlays detections (green circles + label “MINE?”). Keys displayed at top left.
- `telemetry.py` – Telemetry CSV logger: logs detection metadata (timestamp, camera, position, radius, saved path).
- `main.py` – Orchestration: loads config, starts camera threads, runs per-frame detection, draws GUI, handles paging, and writes telemetry/crops.

## Runtime Flow
1. Load config, set logging level.
2. Start one CamWorker per enabled camera.
3. In a loop:
   - Grab latest frame snapshot from each worker.
   - Run detection on frames (Hough circles).
   - Save unsorted crops by camera and log to telemetry.
   - Render tiled GUI (2×2) with overlays.
   - Handle key input (q, [ , ], s).

## Keyboard Controls
- q – Quit
- [ – Previous page
- ] – Next page
- s – Save full frame for visible page cameras to unsorted

## Dataset Strategy
- Unsorted captures are stored as:
  `Mine2/dataset/unsorted/<camera_name>/<timestamp>_<x>_<y>_<r>.png`
- Later, you can curate into:
  - `Mine2/dataset/mine/<camera_name>/...`
  - `Mine2/dataset/not_mine/<camera_name>/...`
  A future enhancement can add a curator tool to re-label and move files.

## Performance Considerations
- RTSP decoding and HoughCircles on 5 feeds is CPU heavy. If needed:
  - Lower resolution via `width/height` in camera config
  - Disable some cameras
  - Increase `min_radius` and `param2` to reduce false positives/detections cost
  - Consider processing every Nth frame

## Windows Notes
- Ensure OpenCV HighGUI is available (opencv-python).
- Some RTSP URLs require ffmpeg support; if streams fail to open, test with VLC first.

## Extension Ideas
- Add optional YOLO-based round-object model for improved accuracy
- Sound / popup alerts on detection
- Recording short video clips around detection
- Network health panel (latency, fps per stream)
- Curator UI to reclassify unsorted into mine/not_mine

## Troubleshooting
- No video: Verify RTSP URL works in VLC; check firewall and network
- High CPU: Reduce resolution or number of active cameras
- No window: Don’t run in headless environment; ensure you have a desktop session
- Frequent reconnects: Increase buffering or check WiFi signal
