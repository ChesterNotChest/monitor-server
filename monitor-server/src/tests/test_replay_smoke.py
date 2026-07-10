"""Clip-replay smoke test — 测试环形缓冲区 + 录制会话 + 产物可用性。

用法: conda run -n monitor-server python test_replay_smoke.py
"""

import os
import sys
import time
import tempfile
import subprocess

# 确保能找到 src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "monitor-server"))

import cv2
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# ⚠️ 必须在任何 SQLAlchemy ORM 操作前导入全部模型，否则 mapper 配置失败
import src.models  # noqa: F401
from src.extensions import Base
from src.service.replay_module.ring_buffer import FrameRingBuffer
from src.service.replay_module.recorder import RecordingSession

# ── 配置 ──
OUTPUT_DIR = tempfile.mkdtemp(prefix="replay_test_")
FPS = 15
WIDTH, HEIGHT = 640, 480
TEST_SECONDS = 5          # 总测试帧数对应的时长
SILENCE_TIMEOUT = 3        # 静默超时（秒），本次测试用短值
VLC_PATH = r"E:\Program Files (x86)\VideoLAN\VLC\vlc.exe"

print(f"[1] 生成 {FPS * TEST_SECONDS} 帧测试图案...")
frames = []
for i in range(FPS * TEST_SECONDS):
    # 彩色背景 + 移动矩形 + 帧号文字
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    hue = (i * 5) % 180
    color_hsv = np.array([[[hue, 200, 200]]], dtype=np.uint8)
    color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0]
    frame[:] = tuple(int(c) for c in color_bgr)

    # 移动白色矩形
    x = (i * 8) % (WIDTH - 100)
    y = HEIGHT // 2 - 50
    cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
    cv2.putText(frame, f"Frame {i}", (10, HEIGHT - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Replay Smoke Test", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # raw BGR24 — 与 recorder FFmpeg 的 -f rawvideo -pix_fmt bgr24 匹配
    frames.append(frame.tobytes())

print(f"   OK — {len(frames)} 帧已生成")

print(f"\n[2] 环形缓冲区测试...")
buf = FrameRingBuffer(max_seconds=10, fps=FPS)
for f in frames:
    buf.push(f)
print(f"   缓冲区长度: {len(buf)} (预期 {FPS * TEST_SECONDS})")

print(f"\n[3] 触发录制...")
# 用 monkeypatch 缩短静默超时
import src.config
original_silence = src.config.settings.RECORD_STOP_SILENCE_SECONDS
src.config.settings.RECORD_STOP_SILENCE_SECONDS = SILENCE_TIMEOUT

try:
    # 创建 DB 会话 —— 导入全部模型以触发 mapper 注册
    db_url = "sqlite:///./test_replay.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    from src.models.recording import Recording
    Recording.__table__.create(bind=engine, checkfirst=True)

    db = Session(bind=engine)

    session = RecordingSession(
        view_id=999,
        buffer=buf,
        cache_path=OUTPUT_DIR,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
    )

    filename = session.start(db)
    print(f"   录制开始: {filename} → {session.output_path}")

    # 模拟持续写帧
    extra_frames_count = SILENCE_TIMEOUT * FPS + 10
    print(f"   写入 {extra_frames_count} 额外帧并等待静默超时...")
    for i in range(extra_frames_count):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = (0, 100 + (i * 2) % 156, 0)
        cv2.putText(frame, f"Recorded Frame {i}", (10, HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        session.push_frame(frame.tobytes())
        time.sleep(0.05)

    # 等待静默监控线程触发停止
    print(f"   等待静默超时 (SILENCE_TIMEOUT={SILENCE_TIMEOUT}s)...")
    timeout = SILENCE_TIMEOUT + 5
    waited = 0
    while not session.is_stopped() and waited < timeout:
        time.sleep(0.5)
        waited += 0.5

    output = session.stop(db)
    db.close()
    print(f"   录制停止, output={output}")

    # ── 验证 ──
    print(f"\n[4] 验证产物...")
    if output and os.path.exists(output):
        size_mb = os.path.getsize(output) / 1024 / 1024
        print(f"   ✅ 文件存在: {output}")
        print(f"   文件大小: {size_mb:.2f} MB")

        # 用 ffprobe 检查视频信息
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", output
        ], capture_output=True, text=True)
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            for stream in info.get("streams", []):
                if stream["codec_type"] == "video":
                    print(f"   编码: {stream.get('codec_name')}, "
                          f"分辨率: {stream.get('width')}x{stream.get('height')}, "
                          f"帧率: {stream.get('r_frame_rate')}")
            duration = float(info.get("format", {}).get("duration", 0))
            print(f"   时长: {duration:.1f}s (预期 ~{TEST_SECONDS + SILENCE_TIMEOUT}s)")
        else:
            print(f"   ⚠️  ffprobe 失败: {result.stderr[:200]}")

        # 尝试用 VLC 播放（可选）
        if os.path.exists(VLC_PATH):
            print(f"\n[5] 尝试用 VLC 打开验证...")
            subprocess.Popen([VLC_PATH, "--play-and-exit", output],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   VLC 已启动，请肉眼确认视频内容正确。")
        else:
            print(f"\n   ⚠️  VLC 未找到: {VLC_PATH}")
    else:
        print(f"   ❌ 产物文件不存在! output={output}")

finally:
    src.config.settings.RECORD_STOP_SILENCE_SECONDS = original_silence

# ── JPEG 格式测试 ──
print(f"\n{'='*60}")
print(f"[JPG] JPEG 格式录制测试...")

jpeg_output_dir = tempfile.mkdtemp(prefix="replay_jpeg_test_")
jpeg_frames = []
for i in range(FPS * TEST_SECONDS):
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = (0, 0, 200)
    cv2.rectangle(frame, (i * 5 % WIDTH, HEIGHT // 3),
                  (i * 5 % WIDTH + 80, HEIGHT * 2 // 3), (255, 255, 0), -1)
    cv2.putText(frame, f"JPEG {i}", (10, HEIGHT - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    _, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    jpeg_frames.append(enc.tobytes())

jpeg_buf = FrameRingBuffer(max_seconds=10, fps=FPS, format="jpeg")
for f in jpeg_frames:
    jpeg_buf.push(f)

jpeg_db = Session(bind=engine)
jpeg_session = RecordingSession(999, jpeg_buf, jpeg_output_dir, WIDTH, HEIGHT, FPS)
jpeg_session.start(jpeg_db)

for i in range(SILENCE_TIMEOUT * FPS + 10):
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = (200, 0, 0)
    cv2.putText(frame, f"JPEG Rec {i}", (10, HEIGHT // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    _, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    jpeg_session.push_frame(enc.tobytes())
    time.sleep(0.05)

time.sleep(SILENCE_TIMEOUT + 2)
jpeg_output = jpeg_session.stop(jpeg_db)
jpeg_db.close()

if jpeg_output and os.path.exists(jpeg_output):
    size_mb = os.path.getsize(jpeg_output) / 1024 / 1024
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", jpeg_output
    ], capture_output=True, text=True)
    if result.returncode == 0:
        info = json.loads(result.stdout)
        dur = float(info.get("format", {}).get("duration", 0))
        codec = info["streams"][0]["codec_name"] if info["streams"] else "?"
        print(f"   ✅ JPEG 产物: {size_mb:.2f} MB, {codec}, {dur:.1f}s")
    else:
        print(f"   ✅ JPEG 产物存在: {size_mb:.2f} MB (ffprobe 失败)")
else:
    print(f"   ❌ JPEG 产物不存在!")

print(f"\n[DONE] 产物路径:\n  raw: {OUTPUT_DIR}\n  jpeg: {jpeg_output_dir}")
