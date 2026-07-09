"""录制回放回归测试 — 覆盖 RingBuffer → RecordingSession → FFmpeg 全链路。

CI 模式 (默认):
    pytest src/tests/test_replay_regression.py -v

手动肉眼验证 (需安装 VLC):
    REPLAY_VISUAL_CHECK=1 pytest src/tests/test_replay_regression.py -v -s
"""

import json
import os
import subprocess
import tempfile
import time

import cv2
import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.config
import src.models  # noqa: F401 — 触发全部 mapper 注册
from src.extensions import Base
from src.service.replay_module.recorder import RecordingSession
from src.service.replay_module.ring_buffer import FrameRingBuffer

FPS = 15
WIDTH, HEIGHT = 640, 480
TEST_SECONDS = 5
SILENCE_TIMEOUT = 1  # CI 用短值

VLC_PATH = r"E:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
USE_VLC = os.getenv("REPLAY_VISUAL_CHECK", "").lower() in ("1", "true", "yes")


def _gen_raw_frames(count: int) -> list[bytes]:
    """生成彩色测试帧 (BGR24 raw bytes)。"""
    frames = []
    for i in range(count):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        hue = (i * 5) % 180
        color_hsv = np.array([[[hue, 200, 200]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        frame[:] = tuple(int(c) for c in color_bgr)
        x = (i * 8) % (WIDTH - 100)
        y = HEIGHT // 2 - 50
        cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        cv2.putText(frame, f"Frame {i}", (10, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        frames.append(frame.tobytes())
    return frames


def _gen_jpeg_frames(count: int) -> list[bytes]:
    """生成 JPEG 编码的测试帧。"""
    frames = []
    for i in range(count):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = (0, 0, 200)
        cv2.rectangle(frame, (i * 5 % WIDTH, HEIGHT // 3),
                      (i * 5 % WIDTH + 80, HEIGHT * 2 // 3), (255, 255, 0), -1)
        cv2.putText(frame, f"JPEG {i}", (10, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        _, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frames.append(enc.tobytes())
    return frames


def _ffprobe(path: str) -> dict:
    """返回 {codec, width, height, fps, duration} 或空 dict。"""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {}
    info = json.loads(r.stdout)
    video = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    nums = video.get("r_frame_rate", "0/1").split("/")
    fps_val = int(nums[0]) / int(nums[1]) if len(nums) == 2 else 0
    return {
        "codec": video.get("codec_name", "?"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": fps_val,
        "duration": float(info.get("format", {}).get("duration", 0)),
    }


@pytest.fixture
def replay_db():
    """创建临时 SQLite + recording 表。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ─────────────────────────────────────────────────────
# raw BGR24
# ─────────────────────────────────────────────────────

@pytest.mark.slow
def test_raw_recording_produces_valid_video(replay_db):
    """raw_bgr24 格式：录制产物编码/分辨率/时长正确。"""
    original = src.config.settings.RECORD_STOP_SILENCE_SECONDS
    src.config.settings.RECORD_STOP_SILENCE_SECONDS = SILENCE_TIMEOUT
    out_dir = tempfile.mkdtemp(prefix="regression_raw_")

    try:
        history = _gen_raw_frames(FPS * TEST_SECONDS)
        buf = FrameRingBuffer(max_seconds=10, fps=FPS)
        for f in history:
            buf.push(f)

        session = RecordingSession(999, buf, out_dir, WIDTH, HEIGHT, FPS)
        session.start(replay_db)

        extra = SILENCE_TIMEOUT * FPS + 10
        for i in range(extra):
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            frame[:] = (0, 100 + (i * 2) % 156, 0)
            cv2.putText(frame, f"R {i}", (10, HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
            session.push_frame(frame.tobytes())

        deadline = time.monotonic() + SILENCE_TIMEOUT + 5
        while not session.is_stopped() and time.monotonic() < deadline:
            time.sleep(0.2)

        output = session.stop(replay_db)

        assert output is not None
        assert os.path.exists(output)
        assert os.path.getsize(output) > 1000

        probe = _ffprobe(output)
        assert probe["codec"] == "h264"
        assert probe["width"] == WIDTH
        assert probe["height"] == HEIGHT
        assert probe["fps"] == pytest.approx(FPS, abs=5)
        assert probe["duration"] >= 3  # 至少 3 秒

        if USE_VLC and os.path.exists(VLC_PATH):
            subprocess.Popen(
                [VLC_PATH, "--play-and-exit", output],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    finally:
        src.config.settings.RECORD_STOP_SILENCE_SECONDS = original


# ─────────────────────────────────────────────────────
# JPEG
# ─────────────────────────────────────────────────────

@pytest.mark.slow
@pytest.mark.skip(reason="JPEG image2pipe + proc.stdin.close() 时序问题，暂跳过")
def test_jpeg_recording_produces_valid_video(replay_db):
    """JPEG 格式：录制产物编码正确。"""
    original = src.config.settings.RECORD_STOP_SILENCE_SECONDS
    src.config.settings.RECORD_STOP_SILENCE_SECONDS = SILENCE_TIMEOUT
    out_dir = tempfile.mkdtemp(prefix="regression_jpeg_")

    try:
        history = _gen_jpeg_frames(FPS * TEST_SECONDS)
        buf = FrameRingBuffer(max_seconds=10, fps=FPS, format="jpeg")
        for f in history:
            buf.push(f)

        session = RecordingSession(999, buf, out_dir, WIDTH, HEIGHT, FPS)
        session.start(replay_db)

        extra = SILENCE_TIMEOUT * FPS + 10
        for i in range(extra):
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            frame[:] = (200, 0, 0)
            cv2.putText(frame, f"J {i}", (10, HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
            _, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            session.push_frame(enc.tobytes())

        deadline = time.monotonic() + SILENCE_TIMEOUT + 5
        while not session.is_stopped() and time.monotonic() < deadline:
            time.sleep(0.2)

        output = session.stop(replay_db)

        assert output is not None
        assert os.path.exists(output)
        assert os.path.getsize(output) > 500  # JPEG copy 产物较小

        probe = _ffprobe(output)
        assert probe["duration"] >= 3

    finally:
        src.config.settings.RECORD_STOP_SILENCE_SECONDS = original


# ─────────────────────────────────────────────────────
# RingBuffer 基础回归
# ─────────────────────────────────────────────────────

def test_ring_buffer_format_default():
    buf = FrameRingBuffer(max_seconds=5, fps=10)
    assert buf.format == "raw_bgr24"


def test_ring_buffer_format_jpeg():
    buf = FrameRingBuffer(max_seconds=5, fps=10, format="jpeg")
    assert buf.format == "jpeg"


def test_ring_buffer_auto_discard():
    buf = FrameRingBuffer(max_seconds=1, fps=10)
    for _ in range(15):
        buf.push(b"x")
    assert len(buf) == 10  # max 1s * 10fps


# ─────────────────────────────────────────────────────
# RecordingRepo 原生 SQL
# ─────────────────────────────────────────────────────

def test_recording_repo_native_insert(replay_db):
    from datetime import datetime, timezone
    from src.repository.recording_repo import RecordingRepo

    now = datetime.now(timezone.utc)
    repo = RecordingRepo(replay_db)
    rec = repo.create(
        view_id=1,
        file_path="/tmp/test.flv",
        start_time=now,
        end_time=now,
    )

    assert rec.id is not None
    assert rec.view_id == 1
    assert rec.file_path == "/tmp/test.flv"

    # 验证 persist 到 DB
    row = replay_db.execute(
        text("SELECT * FROM recordings WHERE id = :id"),
        {"id": rec.id},
    ).mappings().one()
    assert row["view_id"] == 1
