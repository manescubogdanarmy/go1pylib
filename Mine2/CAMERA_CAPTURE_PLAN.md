# Mine2 Camera Capture Plan (No RTSP; UDP unreliable)

This document records what we tried, why RTSP/UDP didn’t work in our setup, what the Unitree Go1 network looks like, and a pragmatic plan to capture camera data going forward. It focuses on enabling Mine2 to receive live frames for detection/logging and to save training data.

## TL;DR
- RTSP on the robot is not available (port 554 closed). The web UIs at /vision or /visiontest don’t expose a standard RTSP endpoint.
- Raw UDP via OpenCV/FFmpeg didn’t receive frames—likely due to networking constraints and/or the Unitree Camera SDK’s proprietary imagetrans format.
- Recommended path: deploy a small camera publisher on the robot that compresses frames to JPEG and publishes them over MQTT topics; extend Mine2 to subscribe and decode. This is robust over Wi‑Fi, easy to firewall, and doesn’t rely on RTSP.

---

## Robot network model (from public Unitree Go1 guides)
- Internal network typically at 192.168.123.0/24 connecting multiple compute boards (Jetson Nano/NX and Raspberry Pi) via an internal switch.
- The Pi also serves a hotspot at 192.168.12.1; a laptop joining that gets a 192.168.12.x address.
- Unitree Camera SDK provides “imagetrans” examples:
  - example_putImagetrans: sends camera streams over UDP.
  - example_getimagetrans: receives and shows via GStreamer.
- Constraints noted in community guides:
  - imagetrans receivers often expected on 192.168.123.x; wireless receiving requires route tweaks on the head Nano and Pi.
  - Autostart camera processes (e.g., point_cloud_node, mqttControlNode, live_human_pose) can hold camera resources and must be killed before SDK examples.

References (community docs): geyang/unitree-go1-setup-guide (guide/), Robotics Knowledge Base Unitree Go1 notes, Unitree Camera SDK README.

---

## What we tried so far (and results)
1) RTSP discovery/probing
   - Test-NetConnection 192.168.123.161:554 → TCP connect failed (closed).
   - Mine2/tools/rtsp_probe.py tried common vendor RTSP paths → timeouts.
   - Conclusion: no built-in RTSP server on the robot.

2) HTTP “vision” endpoints
   - http://192.168.123.161/vision and /visiontest reachable on port 80.
   - Did not reveal a documented RTSP URL. Network panel check for MJPEG stream is pending.

3) Raw UDP via OpenCV/FFmpeg
   - On PC: Mine2/tools/udp_grab.py with udp://@:8554 → timeout, no frames.
   - Likely causes:
     - Sender not running or not targeting the correct IP/port.
     - PC not reachable at 192.168.123.x (earlier it was 192.168.12.60 only).
     - imagetrans may not be standard H264/MJPEG; OpenCV/FFmpeg cannot decode proprietary packets without the official receiver.

4) Network alignment
   - PC was on 192.168.12.60; robot internal net is 192.168.123.x.
   - Suggested adding a secondary 192.168.123.200 IP to Wi‑Fi and opening Windows Firewall for UDP.
   - Full route adjustments on robot (as some guides show) not yet applied.

---

## Why RTSP and raw UDP failed (likely)
- RTSP: Robot doesn’t ship an RTSP server for internal cameras.
- Raw UDP: imagetrans not addressed to PC’s 192.168.123.x, and/or nonstandard format requiring the official receiver.

---

## Capture strategies going forward
Prioritized by simplicity and reliability over Wi‑Fi:

A) Use HTTP/MJPEG or snapshot if exposed by /vision or /visiontest
- Inspect browser DevTools → Network for a streaming (multipart/x-mixed-replace) or snapshot URL.
- If found, put that HTTP URL directly in Mine2 config as the camera URI. OpenCV can read MJPEG over HTTP.
- Pros: Zero deployment on robot. Cons: Might not exist / may be low FPS/resolution.

B) Use Unitree imagetrans with correct routes (official path)
- Apply route tweaks from guides:
  - On head Nano: adjust routes; run example_putImagetrans.
  - On Pi: add route to PC’s 192.168.123.x.
  - On PC: ensure a 192.168.123.x address.
- On PC, run example_getimagetrans (official receiver), then bridge frames to Mine2 (see D).
- Pros: Uses official SDK. Cons: Routing complexity; needs a bridge for Mine2.

C) MQTT frame bridge (recommended)
- Deploy a small publisher on the robot (Jetson/NX) that:
  - Captures frames via Unitree Camera SDK.
  - JPEG-encodes and publishes to MQTT topics per camera at controlled FPS.
- Extend Mine2 with an MQTT camera source:
  - Subscribe, decode JPEG payloads, and feed detection.
- Pros: Robust over Wi‑Fi, firewall-friendly, easy multi-camera. Cons: Small code deployment on robot.

D) Local re-encode to RTSP on PC (bridge)
- Run example_getimagetrans on PC, pipe frames to ffmpeg/MediaMTX to expose rtsp://localhost:8554/cam1 for Mine2.
- Pros: Keeps Mine2 unchanged. Cons: Extra process and transcoding latency.

E) Snapshot sync (dataset-only)
- Periodic snapshot saver on robot then SCP/rsync to PC; Mine2 processes folder.
- Pros: Simple. Cons: No real-time GUI.

---

## Detailed plan: MQTT bridge
This is the most controllable and portable approach for multi-camera, non-RTSP setups.

1) Broker
- Run Mosquitto on the PC (Windows or Docker). Default port 1883; allow LAN clients.
- Optional: username/password and TLS later.

2) Topics
- One topic per camera, e.g.:
  - unitree/cam/front_left
  - unitree/cam/front_right
  - unitree/cam/side_left
  - unitree/cam/side_right
  - unitree/cam/rear
- Payload: JPEG bytes (binary). No retain. QoS 0 or 1 (start with 0).

3) Encoding and sizing
- JPEG quality 70–85 (<300–500 KB/frame typical at 640×480).
- Resize frames to 640×480 or similar.
- Target 2–10 fps/cam depending on Wi‑Fi.

4) Robot publisher (Jetson/NX)
- Outline:
  - Init Unitree Camera SDK capture per camera.
  - For each frame: cv2.imencode('.jpg'), publish via paho-mqtt.
  - Handle reconnects; throttle FPS per camera.
- Run on the Jetson boards that access the cameras; stop conflicting autostart nodes first.

5) PC subscriber (Mine2 integration)
- Add mqtt:// URI support to Mine2 (new worker similar to CamWorker):
  - Parse mqtt://<broker>:1883/<topic>
  - Subscribe, decode JPEG payloads, push into latest-frame queue.
- Config example:
```yaml
cameras:
  - { name: front_left, uri: "mqtt://192.168.123.200:1883/unitree/cam/front_left", enabled: true, width: 640, height: 480 }
```

6) Security and stability
- In lab: start without auth; add auth once stable.
- Use last-will for presence if desired.
- Log pub/sub rates; drop stale frames (latest-only).

7) Bandwidth estimate
- 5 cams × 640×480 × ~150 KB × 5 fps ≈ 3.75 MB/s ≈ 30 Mbps → feasible on solid Wi‑Fi. Tune FPS/quality as needed.

---

## Validation checklist
- Network
  - PC reachable at 192.168.123.x from robot (add secondary IP if needed).
  - Firewall allows TCP 1883 to broker (and UDP only if testing imagetrans).
- Broker
  - Mosquitto running; verify with MQTT Explorer.
- Robot publisher
  - Topics receiving messages; payload sizes/fps as expected.
- Mine2 subscriber
  - GUI shows frames; detection logging and dataset saves work.

---

## Risks and mitigations
- Publisher CPU load: cap FPS; consider hardware-accelerated JPEG.
- Wi‑Fi variability: throttle per-camera FPS; drop frames as needed.
- Broker availability: run broker on robot Pi or PC—choose the more stable host.
- Security: add auth/TLS if outside isolated lab network.

---

## Next actions
1) Decide on strategy: try HTTP/MJPEG from /visiontest; if not available, proceed with MQTT bridge.
2) If proceeding with MQTT:
   - Install Mosquitto on PC; confirm robot can reach it.
   - I’ll add MQTT camera source support in Mine2 and provide a robot-side publisher script leveraging Unitree Camera SDK.
   - Validate at 2–3 fps, then scale up cautiously.

---

## Appendix: Previously attempted commands and outputs
- RTSP probe
  - Test-NetConnection 192.168.123.161 -Port 554 → failed.
  - python Mine2/tools/rtsp_probe.py --host 192.168.123.161 --port 554 → timeouts.
- UDP test
  - python Mine2/tools/udp_grab.py --uri udp://@:8554 → Stream timeout; failed to open.
- HTTP
  - http://192.168.123.161/vision and /visiontest open on port 80, but no documented RTSP.
