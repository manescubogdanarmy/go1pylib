import argparse
from pathlib import Path

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None


def main():
    ap = argparse.ArgumentParser(description="Grab a single frame from a UDP source and save to disk.")
    ap.add_argument("--uri", required=True, help="UDP URI, e.g., udp://@0.0.0.0:8554 or udp://@:8554")
    ap.add_argument("--out", default="udp_frame.jpg", help="Output image path")
    args = ap.parse_args()

    if cv2 is None:
        raise RuntimeError("opencv-python is required. pip install opencv-python")

    uri = args.uri
    if uri.startswith("udp://") and "?" not in uri:
        uri = f"{uri}?overrun_nonfatal=1&fifo_size=50000000"

    cap = cv2.VideoCapture(uri, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise SystemExit(f"Failed to open: {args.uri}")
    # Read a few frames to fill buffers
    frame = None
    for _ in range(20):
        ok, f = cap.read()
        if ok:
            frame = f
            break
    cap.release()
    if frame is None:
        raise SystemExit("No frame received (check sender/port)")
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(outp), frame)
    print(f"Saved: {outp}")


if __name__ == "__main__":
    main()
