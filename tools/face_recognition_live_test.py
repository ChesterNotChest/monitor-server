"""Live face-recognition smoke test.

Camera -> face_recognition -> overlay -> FFmpeg -> RTMP.

Play with VLC:
  rtmp://127.0.0.1:1936/live/face_test
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitor-server"))


def _encode_locations(face_recognition, rgb_frame, locations):
    try:
        return face_recognition.face_encodings(rgb_frame, locations)
    except TypeError as exc:
        if "compute_face_descriptor" not in str(exc) and "incompatible function arguments" not in str(exc):
            raise
        return face_recognition.face_encodings(rgb_frame)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--url", default="rtmp://127.0.0.1:1936/live/face_test")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()

    import face_recognition

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"ERROR: camera {args.camera} is not available")
        return 1

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = int(cap.get(cv2.CAP_PROP_FPS) or 15)
    print(f"camera={args.camera} {width}x{height}@{fps}fps")
    print(f"push={args.url}")

    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel",
        "warning",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-g",
        str(fps),
        "-keyint_min",
        str(fps),
        "-bf",
        "0",
        "-f",
        "flv",
        args.url,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    frame_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: camera frame read failed")
                return 1

            rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
            locations = face_recognition.face_locations(rgb_frame)
            encodings = _encode_locations(face_recognition, rgb_frame, locations) if locations else []

            for top, right, bottom, left in locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 220, 0), 2)
                label = "Stranger" if encodings else "Face"
                cv2.putText(
                    frame,
                    label,
                    (left, max(20, top - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 220, 0),
                    2,
                    cv2.LINE_AA,
                )

            cv2.putText(
                frame,
                f"faces={len(locations)} encodings={len(encodings)}",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            if proc.stdin is None:
                return 1
            try:
                proc.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("ERROR: ffmpeg pipe closed")
                return 1

            frame_count += 1
            if frame_count % fps == 0:
                print(f"frames={frame_count} faces={len(locations)} encodings={len(encodings)}")
            if args.max_frames and frame_count >= args.max_frames:
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if proc.stdin:
            proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=5)

    print(f"done frames={frame_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
