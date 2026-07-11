"""活体摄像头 AI 管线测试。

本地闭环：
  摄像头(cv2) → YOLO 检测 → 标注叠加 → FFmpeg 推流 → :1936 → OBS/VLC 播放

用法：
  # Terminal 1: 启动 Server RTMP 靶子
  cd tools && node rtmp_debug_server.js

  # Terminal 2: 运行此脚本
  conda activate monitor-server
  python tests/test_live_camera.py

  # Terminal 3: 播放
  OBS → 添加媒体源 → rtmp://127.0.0.1:1936/live/test
  或 VLC → 打开网络串流 → rtmp://127.0.0.1:1936/live/test
"""

import sys
from pathlib import Path

import cv2
import numpy as np

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.service.vision_module.vision_yolo.detector import YoloDetector
from src.service.vision_module.vision_annotation import draw_detections


def main():
    # 1. 打开摄像头
    print("[1/5] Opening camera (index 0) ...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No camera found at index 0. Try index 1?")
        return
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    print(f"  Camera: {width}x{height} @ {fps:.1f}fps")

    # 2. 加载 YOLO
    print("[2/5] Loading YOLO ...")
    yolo = YoloDetector()
    if not yolo.load():
        print("ERROR: Failed to load YOLO model")
        return
    print("  YOLO loaded")

    # 3. 启动 FFmpeg 推流到 :1936
    print("[3/5] Starting FFmpeg push to rtmp://127.0.0.1:1936/live/test ...")
    import subprocess
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}", "-r", str(int(fps)),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-f", "flv", "rtmp://127.0.0.1:1936/live/test",
    ]
    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"  FFmpeg PID: {proc.pid}")

    # 4. 主循环
    print("[4/5] Running AI pipeline. Press Ctrl+C to stop.")
    print("      Play: rtmp://127.0.0.1:1936/live/test")
    print("-" * 50)

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # YOLO 检测
            detections = yolo.detect(frame)

            # 标注
            annotated = draw_detections(frame, detections)

            # 推流
            if proc.stdin:
                try:
                    proc.stdin.write(annotated.tobytes())
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"  {frame_count} frames pushed ...")
                except BrokenPipeError:
                    print("FFmpeg pipe broken — stopping")
                    break

    except KeyboardInterrupt:
        print("\n[5/5] Stopping ...")

    cap.release()
    if proc.stdin:
        proc.stdin.close()
    proc.terminate()
    proc.wait()

    print(f"Done. {frame_count} frames processed.")


if __name__ == "__main__":
    main()
