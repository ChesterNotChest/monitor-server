"""Clip-replay smoke test — FrameRingBuffer 基础验证。

注: RecordingSession 已切为 RTMP pull 架构 (yuyu branch)，
不再支持旧 frame-pipe 模式。RecordingSession 集成测试需 SRS 运行。
用法: pytest monitor-server/src/tests/test_replay_smoke.py -v
"""

import pytest
import numpy as np

from src.service.replay_module.ring_buffer import FrameRingBuffer

FPS = 15
WIDTH, HEIGHT = 640, 480
TEST_SECONDS = 5
JPEG_FORMAT = "jpeg"


class TestFrameRingBuffer:
    """环形缓冲区 BGR24 / JPEG 格式读写测试。"""

    def test_push_and_len_raw(self):
        """BGR24 格式: push N 帧后 len == N。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS)
        frames = _generate_raw_frames(FPS * TEST_SECONDS)
        for f in frames:
            buf.push(f)
        assert len(buf) == FPS * TEST_SECONDS

    def test_dump_all_raw(self):
        """BGR24: dump_all 返回全部已写入帧。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS)
        frames = _generate_raw_frames(FPS * TEST_SECONDS)
        for f in frames:
            buf.push(f)
        dumped = buf.dump_all()
        assert len(dumped) == len(frames)

    def test_dump_all_raw_content(self):
        """BGR24: dump_all 内容与写入一致。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS)
        frames = _generate_raw_frames(10)
        for f in frames:
            buf.push(f)
        dumped = buf.dump_all()
        for i, (orig, restored) in enumerate(zip(frames, dumped)):
            assert orig == restored, f"Frame {i} mismatch"

    def test_max_seconds_truncation(self):
        """超出 max_seconds 的旧帧被丢弃。"""
        buf = FrameRingBuffer(max_seconds=2, fps=FPS)
        frames = _generate_raw_frames(FPS * TEST_SECONDS)
        for f in frames:
            buf.push(f)
        expected = min(len(frames), 2 * FPS)
        assert len(buf) == expected

    def test_clear(self):
        """clear() 清空缓冲区。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS)
        for f in _generate_raw_frames(10):
            buf.push(f)
        assert len(buf) == 10
        buf.clear()
        assert len(buf) == 0

    def test_push_and_len_jpeg(self):
        """JPEG 格式: push N 帧后 len == N。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS, format=JPEG_FORMAT)
        frames = _generate_jpeg_frames(FPS * TEST_SECONDS)
        for f in frames:
            buf.push(f)
        assert len(buf) == FPS * TEST_SECONDS

    def test_dump_all_jpeg(self):
        """JPEG: dump_all 返回全部已写入帧。"""
        buf = FrameRingBuffer(max_seconds=10, fps=FPS, format=JPEG_FORMAT)
        frames = _generate_jpeg_frames(FPS * TEST_SECONDS)
        for f in frames:
            buf.push(f)
        assert len(buf.dump_all()) == len(frames)


@pytest.mark.skip(reason="RecordingSession 已改为 RTMP pull 架构，需 SRS 运行才能集成测试")
def test_recording_session_integration():
    """旧 frame-pipe 模式的 RecordingSession 测试已废弃。

    新架构: RecordingSession 从 SRS RTMP 拉流，push_frame 是 no-op。
    如需测试录制链路，请启动 SRS 后手动跑 playbook。
    """
    pass


# ── helpers ──

def _generate_raw_frames(n: int) -> list[bytes]:
    import cv2
    frames = []
    for i in range(n):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = ((i * 5) % 180, 200, 200)
        cv2.putText(frame, f"Frame {i}", (10, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        frames.append(frame.tobytes())
    return frames


def _generate_jpeg_frames(n: int) -> list[bytes]:
    import cv2
    frames = []
    for i in range(n):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = (0, 0, 200)
        cv2.putText(frame, f"JPEG {i}", (10, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        _, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frames.append(enc.tobytes())
    return frames
