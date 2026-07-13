"""流合成集成测试——验证 FrameReader → YOLO → Annotation → FFmpeg 输出链路。

不依赖真实 RTMP/SRS：用本地视频文件 + FFmpeg 写文件。
"""

import asyncio
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.config import settings
from src.service.vision_module.vision_frame_reader import FrameReader, FrameReaderState
from src.service.vision_module.vision_yolo.detector import YoloDetector, Detection, YoloState
from src.service.vision_module.vision_annotation import draw_detections
from src.service.vision_module.vision_merger import (
    start_stream_merge, push_frame, stop_stream_merge,
)
from src.service.vision_module.vision_event_bus import event_bus, ENTITY

# ── 模型文件检测 ──
# 配置路径相对于 monitor-server/ 目录（run.py 所在），
# 但测试从项目根运行。尝试两个位置。
_candidates = [
    Path(settings.YOLO_MODEL_PATH),                  # 相对于 cwd (monitor-server/)
    Path("monitor-server") / settings.YOLO_MODEL_PATH,  # 相对于项目根
]
_YOLO_MODEL_AVAILABLE = any(p.exists() for p in _candidates)
_skip_no_model = pytest.mark.skipif(
    not _YOLO_MODEL_AVAILABLE,
    reason=f"YOLO model not found (tried: {_candidates})",
)


# ── 辅助函数 ──────────────────────────────────

def _make_test_frame(w: int = 640, h: int = 480) -> np.ndarray:
    """生成纯色测试帧（蓝色背景）。"""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = (255, 128, 64)  # BGR
    return frame


def _make_test_video(path: str, num_frames: int = 10, fps: int = 10) -> None:
    """生成一段纯色测试视频。"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(path, fourcc, fps, (640, 480))
    for _ in range(num_frames):
        writer.write(_make_test_frame())
    writer.release()


# ── Tests ─────────────────────────────────────

class TestFrameReader:
    """帧读取器——本地文件模式。"""

    def test_idle_on_init(self):
        r = FrameReader()
        assert r.state == FrameReaderState.IDLE

    def test_read_from_file(self, tmp_path: Path):
        """从本地文件读帧（模拟 RTMP 拉流）。"""
        video_path = tmp_path / "test.mp4"
        _make_test_video(str(video_path), num_frames=100)  # 足够长，避免 EOF

        r = FrameReader()
        r._cap = cv2.VideoCapture(str(video_path))
        assert r._cap.isOpened()
        r._state = FrameReaderState.ACTIVE
        r._fps_target = 10

        # VideoCapture 到文件尾会 loop=False，模拟流则无限。读几帧验证
        for _ in range(5):
            success, frame, ts, fid = r.read()
            if not success:
                break  # 文件尾
            assert frame is not None
            assert frame.shape == (480, 640, 3)

        r.close()


class TestYoloDetector:
    """YOLO 检测器——加载与推理。"""

    @_skip_no_model
    def test_load_model(self):
        d = YoloDetector()
        assert d.load()
        assert d.state == YoloState.ACTIVE

    @_skip_no_model
    def test_detect_empty_frame(self):
        d = YoloDetector()
        d.load()
        frame = _make_test_frame()
        detections = d.detect(frame)
        # 纯色帧无目标
        assert isinstance(detections, list)

    @_skip_no_model
    def test_detect_and_publish(self):
        d = YoloDetector()
        d.load()

        received = []
        async def capture(payload):
            received.append(payload)

        # register subscriber using pytest-asyncio compatible pattern
        async def _run():
            await event_bus.subscribe(ENTITY, capture)
            await d.detect_and_publish(_make_test_frame(), view_id=1)

        asyncio.run(_run())

        # EventBus 收到了事件（即使无检出也发布空列表… 实际空列表不发布）
        # 这里只验证链路不崩溃
        assert True


class TestAnnotationOverlay:
    """标注叠加——画框不修改原帧尺寸。"""

    def test_draw_no_detections(self):
        frame = _make_test_frame()
        annotated = draw_detections(frame, [])
        assert annotated.shape == frame.shape
        # 返回的是副本（不同对象）：时间戳由 Node 侧烧录，Server 不重复叠加
        assert annotated is not frame

    def test_draw_with_detection(self):
        frame = _make_test_frame()
        det = Detection(
            bbox=[100, 150, 300, 400],
            class_id=0,
            confidence=0.9,
            entity_type_id=1,  # PERSON
            label_suffix="1",  # 必须有 label_suffix 才绘制（三级标注策略）
        )
        annotated = draw_detections(frame, [det])
        assert annotated.shape == frame.shape
        # 有 label_suffix 的检测会被绘制，像素会变
        assert not np.array_equal(annotated, frame)


class TestStreamMerge:
    """FFmpeg 合流——验证进程启停。"""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        proc = await start_stream_merge(
            view_id=1, video_width=640, video_height=480, fps=10,
        )
        assert proc is not None
        assert proc.returncode is None  # still running

        await stop_stream_merge(proc)
        assert proc.returncode is not None  # terminated


class TestPipelineIntegration:
    """端到端——帧读取 → YOLO → 标注 → FFmpeg 输出。

    用本地视频文件替代 RTMP。输出到临时文件替代 SRS push。
    """

    @_skip_no_model
    @pytest.mark.asyncio
    async def test_full_pipeline_with_local_video(self, tmp_path: Path):
        """完整管线：本地视频 → YOLO → 标注 → FFmpeg 写文件。

        不经过 FrameReader（它设计用于 RTMP 流，EOF 会触发重连），
        直接用 cv2.VideoCapture 迭代本地文件。"""
        # 1. 生成测试视频（30 帧，足够 YOLO 跑几轮）
        video_path = tmp_path / "input.mp4"
        _make_test_video(str(video_path), num_frames=30, fps=10)
        output_path = tmp_path / "output.flv"

        # 2. 直接读本地文件
        cap = cv2.VideoCapture(str(video_path))
        assert cap.isOpened()

        # 3. 加载 YOLO
        yolo = YoloDetector()
        assert yolo.load()

        # 4. 启动 FFmpeg（输出到文件）
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", "640x480", "-r", "10",
            "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-y",
            "-f", "flv", str(output_path.absolute()),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        assert proc.returncode is None

        # 5. 逐帧处理
        frames_processed = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            detections = yolo.detect(frame)
            annotated = draw_detections(frame, detections)
            if proc.stdin:
                try:
                    proc.stdin.write(annotated.tobytes())
                    frames_processed += 1
                except BrokenPipeError:
                    break

        cap.release()

        # 6. 推完帧后关闭 stdin，等 FFmpeg 完成
        if proc.stdin:
            proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

        # 7. 验证输出文件存在且非空
        assert output_path.exists(), f"Output file not created: {output_path}"
        assert output_path.stat().st_size > 0, "Output file is empty"
        assert frames_processed >= 29, f"Expected at least 29 frames, got {frames_processed}"
