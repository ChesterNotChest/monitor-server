"""AI Pipeline 调度器——模块对接协议与主循环。

FrameContext 是所有帧处理模块的统一数据契约。
AIPipeline 管理模块注册、主循环启停、异常隔离。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import numpy as np

from src.config import settings
from src.constants import YOLOEntityType
from src.service.vision_module.vision_frame_reader import FrameReader, FrameReaderState
from src.service.vision_module.vision_yolo.detector import YoloDetector, Detection, YoloState
from src.service.vision_module.vision_annotation import draw_detections, _face_labels
from src.service.vision_module.vision_merger import (
    start_stream_merge, push_frame, stop_stream_merge,
)
from src.service.vision_module.vision_types import Track

logger = logging.getLogger(__name__)

# ── 数据契约 ──────────────────────────────────

@dataclass
class FrameContext:
    """每帧上下文——所有模块的统一输入。

    B/C 模块通过 register_frame_hook 接收此对象。
    """
    frame: np.ndarray                # BGR24, (H, W, 3)
    frame_id: int                    # 单调递增
    timestamp: float                 # Unix 相对时间（秒）
    detections: list[Detection]      # YOLO 原始输出
    tracks: list[Track] | None = None  # ByteTrack 产出（B 模块填充）
    view_id: int = 0


# ── 类型别名 ──────────────────────────────────

FrameHook = Callable[[FrameContext], Awaitable[None]]


# ── 标注富化 ──────────────────────────────────

def _bbox_iou(a: list[float], b: list[float]) -> float:
    """Compute IoU between two bboxes [x1,y1,x2,y2]."""
    x_left = max(a[0], b[0])
    y_top = max(a[1], b[1])
    x_right = min(a[2], b[2])
    y_bottom = min(a[3], b[3])
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    inter = (x_right - x_left) * (y_bottom - y_top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _enrich_detection_labels(
    detections: list[Detection],
    tracks: list[Track] | None,
    face_labels: dict[int, str],
) -> None:
    """Match person detections to ByteTrack tracks by IoU, set label_suffix.

    Mutates detections in-place.  Only person-class detections get enriched.
    """
    if not tracks:
        return
    for det in detections:
        if det.entity_type_id != YOLOEntityType.PERSON:
            continue
        best_track: Track | None = None
        best_iou = 0.0
        for track in tracks:
            iou = _bbox_iou(det.bbox, track.bbox)
            if iou > best_iou:
                best_iou = iou
                best_track = track
        if best_track is not None and best_iou > 0.3:
            parts = [f"ID {best_track.track_id}"]
            face = face_labels.get(best_track.track_id)
            if face:
                parts.append(f"Face: {face}")
            det.label_suffix = " ".join(parts)


# ── Pipeline 调度器 ───────────────────────────

class AIPipeline:
    """AI 管线调度器。

    管理 FrameReader → YOLO → hooks → Annotation → StreamMerger 主循环。
    B/C 模块通过 register_frame_hook() 注册帧处理回调。
    """

    def __init__(self) -> None:
        self._reader = FrameReader()
        self._yolo = YoloDetector()
        self._frame_hooks: list[FrameHook] = []
        self._merge_proc: asyncio.subprocess.Process | None = None
        self._latest_frame: np.ndarray | None = None
        self._next_frame_due: float = 0.0  # 下一帧的绝对推送时刻
        self._push_interval: float = 1.0 / max(settings.FPS_TARGET, 1)
        self._running = False
        self._task: asyncio.Task | None = None

    # ── Hook registration ─────────────────────

    def register_frame_hook(self, hook: FrameHook) -> None:
        """注册帧处理回调。B/C 模块用此接入主循环。

        每个 frame 依次调用所有 hook。单个 hook 异常不中断主循环。
        """
        if hook not in self._frame_hooks:
            self._frame_hooks.append(hook)

    # ── Lifecycle ──────────────────────────────

    async def start(self, view_id: int, video_id: int, video_name: str,
                    audio_id: int | None = None,
                    audio_name: str = "") -> bool:
        """启动 AI 管线。

        Args:
            view_id: View 数据库 ID。
            video_id: VideoDevice 数据库 ID。
            video_name: VideoDevice 名称（用于 RTMP 拉流命名）。
            audio_id: AudioDevice 数据库 ID（可选）。

        Returns:
            True if pipeline started successfully.
        """
        if self._running:
            logger.warning("Pipeline already running")
            return False

        # 1. 加载 YOLO
        if not self._yolo.load():
            return False

        # 2. 打开帧读取器
        if not self._reader.open(video_id, video_name):
            return False

        # 3. 启动 FFmpeg 合流
        #    用 YOLO 输入尺寸作为视频尺寸（大多数视频是 640x480 或类似）
        #    实际尺寸从第一帧获取
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(view_id, audio_id, audio_name),
            name=f"ai-pipeline-view-{view_id}",
        )
        logger.info("AIPipeline started for view_id=%d", view_id)
        return True

    async def stop(self) -> None:
        """停止 AI 管线。"""
        logger.info("AIPipeline stopping ...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._reader.close()
        if self._merge_proc:
            await stop_stream_merge(self._merge_proc)
            self._merge_proc = None
        logger.info("AIPipeline stopped")

    # ── Main loop ─────────────────────────────

    async def _run_loop(self, view_id: int, audio_id: int | None,
                         audio_name: str = "") -> None:
        """主循环：逐帧读取 → YOLO → hooks → 标注 → 推流。"""
        merge_started = False
        _loop_frame_count = 0
        _loop_last_log = time.monotonic()

        while self._running:
            _loop_frame_count += 1
            _t0 = time.monotonic()
            success, frame, ts, fid = self._reader.read()
            _t1 = time.monotonic()
            if not success:
                if self._reader.state == FrameReaderState.ERROR:
                    logger.error("FrameReader in ERROR state — stopping pipeline")
                    break
                continue  # 断流重连中

            # 首帧启动 FFmpeg merge
            if not merge_started:
                h, w = frame.shape[:2] if frame is not None else (480, 640)
                # 推流帧率对齐节流速率，而非原始源帧率
                fps = settings.FPS_TARGET
                self._merge_proc = await start_stream_merge(
                    view_id, w, h, fps, audio_id, audio_name,
                )
                if self._merge_proc is None:
                    logger.error("Failed to start stream merge — stopping pipeline")
                    break
                merge_started = True

            # YOLO 检测
            detections = await self._yolo.detect_and_publish(frame, view_id)
            _t2 = time.monotonic()

            # 帧上下文
            ctx = FrameContext(
                frame=frame,
                frame_id=fid,
                timestamp=ts,
                detections=detections,
                view_id=view_id,
            )

            # 调用注册的帧钩子（B/C 模块）
            for hook in self._frame_hooks:
                try:
                    await hook(ctx)
                except Exception:
                    logger.exception("Frame hook %s failed", getattr(hook, "__name__", hook))
            _t3 = time.monotonic()

            # 标注叠加 — 一步到位：用 Track/Face 信息富化 Detection 标签，单遍绘制
            _enrich_detection_labels(detections, ctx.tracks, _face_labels)
            annotated = draw_detections(frame, detections)
            _t4 = time.monotonic()

            # 推流 — 绝对时钟调度：按固定 15fps 节拍推，不等相对间隔
            if self._merge_proc:
                _now = time.monotonic()
                if self._next_frame_due == 0.0:
                    self._next_frame_due = _now
                if _now >= self._next_frame_due:
                    await push_frame(self._merge_proc, annotated)
                    self._next_frame_due += self._push_interval
                # 睡到下一帧的绝对时刻（避免累积漂移）
                _wait = self._next_frame_due - time.monotonic()
                if _wait > 0:
                    await asyncio.sleep(_wait)

            # 可观测性：每 5 秒打印一次帧率 + 分段耗时 + 端到端延迟
            _tn = time.monotonic()
            if _tn - _loop_last_log >= 5.0:
                _fps = _loop_frame_count / (_tn - _loop_last_log)
                _read_ms = (_t1 - _t0) * 1000
                _yolo_ms = (_t2 - _t1) * 1000
                _hooks_ms = (_t3 - _t2) * 1000
                _draw_ms = (_t4 - _t3) * 1000
                # 管线内延迟 = 从读帧开始到推送完成的耗时
                _latency_ms = (_tn - _t0) * 1000
                logger.info("[obs] FPS=%.1f | r=%.0f y=%.0f hk=%.0f dr=%.0f ms | latency=%.0f ms",
                            _fps, _read_ms, _yolo_ms, _hooks_ms, _draw_ms, _latency_ms)
                _loop_frame_count = 0
                _loop_last_log = _tn

        logger.info("Pipeline main loop exited for view_id=%d", view_id)
