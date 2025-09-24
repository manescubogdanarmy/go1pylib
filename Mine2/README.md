# Mine2 (Multi-Camera Mine Monitor)

Windows-only multi-camera (RTSP/UDP/device) monitoring tool for Unitree Go1 EDU. Displays up to 4 feeds per page (2×2) with paging for all 5 cameras. Runs Hough circle detection on each stream, overlays bounding circles and logs detections. Passive operation: you drive with the remote; Mine2 only observes and logs.

## Quick Start
1. Edit `Mine2/mine2_config.yaml`:
   - Replace `rtsp://<robot-ip>/...` with your actual stream URLs (RTSP/UDP).
2. Install deps:
```
pip install .[mine]
```
3. Run:
```
python Mine2/main.py --config Mine2/mine2_config.yaml
```

Controls:
- q = quit
- [ / ] = previous / next page (2×2 grid)
- s = save full frames (unsorted) for visible page cameras

Detections:
- Circles are outlined in green with label “MINE?”
- Console logs a line per detection with camera name and radius
- Cropped detections saved to `Mine2/dataset/unsorted/<camera_name>/`

## Notes
- This app does not send any robot commands; it only observes.
- For heavy CPU load (5 streams), reduce resolution in config (`width`, `height`) or disable some cameras.
- If RTSP reconnects are needed, the stream worker auto-retries when `.read()` fails.

See `documentation.md` for deeper architecture and extension points.

## Finding your RTSP URLs (optional helper)
- If your cameras are generic IP cams, you can probe common RTSP paths using the helper:

```powershell
python Mine2/tools/rtsp_probe.py --host 192.168.123.161 --port 554 --user admin --password Your%21Pass
```

- Tips:
   - If a password has special characters, URL‑encode them when embedding (e.g., `#` → `%23`, `@` → `%40`).
   - You can omit `--user/--password` and let clients prompt (e.g., VLC).
   - Use an ONVIF discovery tool on Windows (e.g., ONVIF Device Manager) to list exact RTSP profiles.

   ## Using Unitree Camera SDK imagetrans (UDP)
   If the Go1 doesn’t offer RTSP, use Unitree’s Camera SDK sender on the robot and receive via UDP:

   1) On the robot: run the SDK example sender (example_putImagetrans) to a known UDP port (e.g., 8554).
       - Ensure the robot’s autostart camera processes are stopped per Unitree docs before running the example.

   2) On your PC, verify reception with the helper:

   ```powershell
   python Mine2/tools/udp_grab.py --uri udp://@:8554 --out udp_test.jpg
   ```

   3) Configure Mine2 to listen to the same UDP port (replace a camera URI):

   ```yaml
   cameras:
      - { name: front_left, uri: "udp://@:8554", enabled: true }
   ```

   Notes:
   - For UDP sources, the app uses FFmpeg backend and larger FIFO to reduce packet drops.
   - You can run multiple senders on different ports (8554, 8555, …) and point each camera entry to a port.
