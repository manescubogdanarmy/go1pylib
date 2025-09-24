import argparse
import sys
from typing import List, Optional

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore


DEFAULT_PATHS: List[str] = [
    "/Streaming/Channels/101",  # Hikvision main
    "/Streaming/Channels/102",  # Hikvision sub
    "/cam/realmonitor?channel=1&subtype=0",  # Dahua main
    "/cam/realmonitor?channel=1&subtype=1",  # Dahua sub
    "/h264/ch1/main/av_stream",  # Hik-like
    "/h264/ch1/sub/av_stream",
    "/unicast/c1/s0/live",  # Uniview main
    "/unicast/c1/s1/live",  # Uniview sub
    "/profile1/media.smp",  # Hanwha/Samsung
    "/axis-media/media.amp",  # Axis
    "/live",  # generic
    "/live.sdp",  # generic
    "/stream1",  # generic
    "/ch0_0.264",  # Jooan main
    "/ch0_1.264",  # Jooan sub
]


def build_url(host: str, port: int, path: str, user: Optional[str], password: Optional[str]) -> str:
    auth = ""
    if user:
        if password is None:
            password = ""
        auth = f"{user}:{password}@"
    return f"rtsp://{auth}{host}:{port}{path}"


def try_open(url: str, timeout_ms: int = 3000) -> bool:
    if cv2 is None:
        raise RuntimeError("opencv-python is required to run this probe. Install with: pip install opencv-python")
    cap = cv2.VideoCapture(url)
    ok = cap.isOpened()
    if not ok:
        cap.release()
        return False
    # Try to grab 1 frame quickly
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ret, _ = cap.read()
    cap.release()
    return bool(ret)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe common RTSP URL patterns against a host.")
    parser.add_argument("--host", required=True, help="Camera host/IP, e.g., 192.168.123.161")
    parser.add_argument("--port", type=int, default=554, help="RTSP port (default 554)")
    parser.add_argument("--user", help="Username (optional)")
    parser.add_argument("--password", help="Password (optional, URL-encode special chars if embedded)")
    parser.add_argument("--paths", nargs="*", help="Override paths to try; if omitted, tries common defaults")
    args = parser.parse_args()

    paths = args.paths if args.paths else DEFAULT_PATHS
    tried: List[str] = []
    successes: List[str] = []

    print(f"Probing RTSP endpoints on {args.host}:{args.port} ...")

    # 1) Try with provided credentials (if any)
    for p in paths:
        url = build_url(args.host, args.port, p, args.user, args.password)
        tried.append(url)
        try:
            if try_open(url):
                print(f"SUCCESS: {url}")
                successes.append(url)
        except Exception as e:
            print(f"FAIL: {url} -> {e}")

    # 2) If no success and no creds provided, try without creds explicitly
    if not successes and (not args.user and not args.password):
        for p in paths:
            url = build_url(args.host, args.port, p, None, None)
            if url in tried:
                continue
            try:
                if try_open(url):
                    print(f"SUCCESS (no-auth): {url}")
                    successes.append(url)
            except Exception as e:
                print(f"FAIL: {url} -> {e}")

    if successes:
        print("\nFirst working URL:")
        print(successes[0])
        print("\nTip: If your password contains special characters, URL-encode them (e.g., # -> %23, @ -> %40).")
        return 0
    else:
        print("\nNo working RTSP URL found among common patterns.")
        print("- Verify the device has RTSP enabled and the port is open (default 554).")
        print("- Try ONVIF Device Manager on Windows to discover exact profiles.")
        print("- Test in VLC: Media -> Open Network Stream -> rtsp://<host> (let it prompt for credentials).")
        return 2


if __name__ == "__main__":
    sys.exit(main())
