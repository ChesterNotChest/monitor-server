"""Live camera Part B visualization.

Local loop:
  camera -> YOLO -> ByteTrack/Face/SlowFast/Fence -> overlay -> FFmpeg -> RTMP.

Play the stream with:
  rtmp://127.0.0.1:1936/live/test
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.service.vision_module.vision_annotation import draw_detections, draw_part_b_overlay
from src.service.vision_module.vision_face import FaceRecognizer, FaceResultStatus
from src.service.vision_module.vision_fence.fence_engine import FenceEngine, _FenceConfig
from src.service.vision_module.vision_slowfast import SlowFastRunner
from src.service.vision_module.vision_tracking import ByteTracker
from src.service.vision_module.vision_types import Track
from src.service.vision_module.vision_yolo.detector import YoloDetector


def _crop(frame: np.ndarray, track: Track) -> np.ndarray | None:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = [int(round(value)) for value in track.bbox]
    x1 = max(0, min(width, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height, y1))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def _demo_fence(width: int, height: int) -> _FenceConfig:
    return _FenceConfig(
        id=1,
        name="DemoFence",
        coords=[
            (width * 0.20, height * 0.18),
            (width * 0.80, height * 0.18),
            (width * 0.80, height * 0.92),
            (width * 0.20, height * 0.92),
        ],
        dwell_time=2,
        density=0.4,
        leave_frames=10,
    )


def main() -> None:
    print("[1/6] Opening camera (index 0) ...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No camera found at index 0. Try index 1.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    print(f"  Camera: {width}x{height} @ {fps:.1f}fps")

    print("[2/6] Loading YOLO ...")
    yolo = YoloDetector()
    if not yolo.load():
        print("ERROR: Failed to load YOLO model")
        return
    print("  YOLO loaded")

    print("[3/6] Initializing Part B modules ...")
    tracker = ByteTracker()
    face_recognizer = FaceRecognizer()
    slowfast_runner = SlowFastRunner(enable_real_kinetics=True, enable_real_ava=True)
    fence = _demo_fence(width, height)
    fence_engine = FenceEngine(view_id=0, fences=[fence])
    face_labels: dict[int, str] = {}
    action_labels: dict[int, str] = {}
    fence_labels: dict[int, str] = {}
    print("  Overlay: track_id + face + action + fence")

    print("[4/6] Starting FFmpeg push to rtmp://127.0.0.1:1936/live/test ...")
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(int(fps)),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-pix_fmt", "yuv420p",
        "-g", str(int(fps)),
        "-keyint_min", str(int(fps)),
        "-bf", "0",
        "-x264-params", "repeat-headers=1",
        "-f", "flv",
        "rtmp://127.0.0.1:1936/live/test",
    ]
    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"  FFmpeg PID: {proc.pid}")

    print("[5/6] Running Part B pipeline. Press Ctrl+C to stop.")
    print("      Play: rtmp://127.0.0.1:1936/live/test")
    print("-" * 50)

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            detections = yolo.detect(frame)
            tracks = tracker.update(detections)

            for result in face_recognizer.recognize(frame, tracks):
                if result.result == FaceResultStatus.NORMAL and result.person_name:
                    face_labels[result.track_id] = result.person_name
                elif result.result == FaceResultStatus.STRANGER:
                    face_labels[result.track_id] = "Stranger"
                else:
                    face_labels[result.track_id] = "NO_RESULT"

            for track in tracks:
                crop = _crop(frame, track)
                if crop is None:
                    continue
                action_results = slowfast_runner.enqueue(track.track_id, crop)
                if action_results:
                    action_labels[track.track_id] = ", ".join(result.label for result in action_results)
                else:
                    action_labels.setdefault(track.track_id, "pending")

            for event in fence_engine.check(tracks, time.monotonic()):
                fence_labels[event.track_id] = "ENTERED" if event.entered else "OUT"

            annotated = draw_detections(frame, detections)
            annotated = draw_part_b_overlay(
                annotated,
                tracks,
                face_labels=face_labels,
                action_labels=action_labels,
                fence_labels=fence_labels,
                fence_polygons=[fence.coords],
            )

            if proc.stdin:
                try:
                    proc.stdin.write(annotated.tobytes())
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"  {frame_count} frames pushed ...")
                except BrokenPipeError:
                    print("FFmpeg pipe broken; stopping")
                    break

    except KeyboardInterrupt:
        print("\n[6/6] Stopping ...")
    finally:
        cap.release()
        if proc.stdin:
            proc.stdin.close()
        proc.terminate()
        proc.wait()

    print(f"Done. {frame_count} frames processed.")


if __name__ == "__main__":
    main()
