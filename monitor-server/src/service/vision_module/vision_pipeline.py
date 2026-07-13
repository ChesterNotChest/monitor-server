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
from src.service.vision_module.vision_annotation import (
    draw_detections, draw_action_regions, draw_fence_polygons,
    _face_labels, _fence_labels, _action_labels,
)
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
    action_regions: dict[int, tuple[int, int, int, int]] | None = None  # SlowFast padded crop
    fence_polygons: list[list[tuple[float, float]]] | None = None  # 围栏多边形
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
    fence_labels: dict[int, str] | None = None,
    action_labels: dict[int, str] | None = None,
) -> None:
    """Match person detections to ByteTrack tracks by IoU, set label_suffix.

    Mutates detections in-place.  Only person-class detections get enriched.
    """
    if not tracks:
        return
    fence_labels = fence_labels or {}
    action_labels = action_labels or {}
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
            tid = best_track.track_id
            parts = [f"ID {tid}"]
            face = face_labels.get(tid)
            if face:
                parts.append(f"Face: {face}")
            fence = fence_labels.get(tid)
            if fence:
                parts.append(fence)
            action = action_labels.get(tid)
            if action:
                parts.append(action)
            det.label_suffix = " ".join(parts)
        if any(d.label_suffix for d in detections if d.entity_type_id == YOLOEntityType.PERSON):
            logger.debug("[Enrich] face=%s fence=%s action=%s",
                         {k: v for k, v in face_labels.items()},
                         {k: v for k, v in fence_labels.items()},
                         {k: v for k, v in action_labels.items()})


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
        self._video_id: int = 0
        self._video_name: str = ""

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

        # 保存拉流参数——断流重连时需要
        self._video_id = video_id
        self._video_name = video_name

        # 1. 加载 YOLO
        if not self._yolo.load():
            return False

        # 2. 打开帧读取器（失败不阻止——_run_loop 会重试）
        self._reader.open(video_id, video_name)

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
        _hold_count = 0
        _push_count = 0
        _loop_last_log = time.monotonic()

        while self._running:
            # ── 时钟门控：等够整拍再开始处理，消除 asyncio 拥堵偏差 ──
            _now = time.monotonic()
            if self._next_frame_due == 0.0:
                self._next_frame_due = _now
            _wait = self._next_frame_due - _now
            if _wait > 0:
                await asyncio.sleep(_wait)
            elif _wait < -self._push_interval:
                # 落后超过 1 帧：跳帧追赶
                self._next_frame_due = time.monotonic()
            self._next_frame_due += self._push_interval

            _loop_frame_count += 1
            _t0 = time.monotonic()
            success, frame, ts, fid = self._reader.read()
            _t1 = time.monotonic()
            if not success:
                if self._reader.state == FrameReaderState.ERROR:
                    logger.error("FrameReader in ERROR state — attempting reopen")
                    if not await self._reopen_reader():
                        logger.error("FrameReader reopen failed — stopping pipeline")
                        break
                    self._next_frame_due = time.monotonic()
                elif self._latest_frame is not None:
                    # 断流重连中——复制上一帧填空，防止灰屏
                    if self._merge_proc:
                        await push_frame(self._merge_proc, self._latest_frame)
                    _hold_count += 1
                continue

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
            _enrich_detection_labels(detections, ctx.tracks, _face_labels,
                                         _fence_labels, _action_labels)
            annotated = draw_detections(frame, detections)
            if ctx.action_regions:
                annotated = draw_action_regions(annotated, ctx.action_regions)
            # 围栏绘制
            if ctx.fence_polygons is not None:
                if ctx.fence_polygons:
                    logger.info("[Fence] drawing %d polygon(s)", len(ctx.fence_polygons))
                    annotated = draw_fence_polygons(annotated, ctx.fence_polygons)
                elif _loop_frame_count <= 2:
                    logger.info("[Fence] ctx.fence_polygons exists but is EMPTY")
            elif _loop_frame_count <= 2:
                logger.info("[Fence] ctx.fence_polygons is None (process_frame not setting it?)")
            _t4 = time.monotonic()

            # 推流 + 缓存用于断流时 frame hold
            self._latest_frame = annotated
            if self._merge_proc:
                await push_frame(self._merge_proc, annotated)
                _push_count += 1

            # 录制：每帧推入环形缓冲区
            from src.service import replay_task
            replay_task.push_frame(view_id, annotated.tobytes())

            # 可观测性：每 5 秒打印一次帧率 + 分段耗时 + 端到端延迟
            _tn = time.monotonic()
            if _tn - _loop_last_log >= 5.0:
                _fps = _loop_frame_count / (_tn - _loop_last_log)
                _read_ms = (_t1 - _t0) * 1000
                _yolo_ms = (_t2 - _t1) * 1000
                _hooks_ms = (_t3 - _t2) * 1000
                _draw_ms = (_t4 - _t3) * 1000
                # 管线内延迟 + 帧在 OpenCV 缓冲中的滞留时间
                _pipe_ms = (_tn - _t0) * 1000
                _frame_age = (time.time() - (self._reader.open_time + ts)) if self._reader.open_time > 0 else 0
                # RTMP 缓冲深度: 流时间戳 vs 墙钟的差距
                # buf > 1000ms → RTMP 有堆积；buf 持续增长 → 「隔夜效应」
                _buf_ms = 0.0
                if self._reader.open_time > 0 and self._reader.stream_pos_ms > 0:
                    _elapsed = (time.time() - self._reader.open_time) * 1000.0
                    _buf_ms = _elapsed - self._reader.stream_pos_ms
                logger.info("[obs] FPS=%.1f | r=%.0f y=%.0f hk=%.0f dr=%.0f ms | pipe=%.0f age=%.0fms buf=%.0fms hold=%d sink=%d",
                            _fps, _read_ms, _yolo_ms, _hooks_ms, _draw_ms, _pipe_ms,
                            _frame_age * 1000, _buf_ms, _hold_count,
                            _loop_frame_count - _push_count)
                _loop_frame_count = 0
                _hold_count = 0
                _push_count = 0
                _loop_last_log = _tn

        logger.info("Pipeline main loop exited for view_id=%d", view_id)

    # ── Reopen helpers ──────────────────────────

    _REOPEN_INITIAL_BACKOFF = 2.0
    _REOPEN_MAX_BACKOFF = 60.0
    _REOPEN_BACKOFF_MULT = 2.0
    _REOPEN_MAX_ATTEMPTS = 10

    async def _reopen_reader(self) -> bool:
        """Attempt to reopen FrameReader with exponential backoff.

        Retries indefinitely — pipeline survives transient RTMP outages.
        After max attempts, resets counter and continues at max backoff interval.
        """
        self._reader.reset_error()
        attempt = 0
        while True:
            attempt += 1
            backoff = min(
                self._REOPEN_INITIAL_BACKOFF * (self._REOPEN_BACKOFF_MULT ** (attempt - 1)),
                self._REOPEN_MAX_BACKOFF,
            )
            logger.warning(
                "FrameReader reopen attempt %d in %.1fs ...",
                attempt, backoff,
            )
            await asyncio.sleep(backoff)
            if self._reader.open(self._video_id, self._video_name):
                logger.info("FrameReader reopened successfully (attempt %d)", attempt)
                return True
            # stop logging every attempt beyond 10 to reduce noise
            if attempt > self._REOPEN_MAX_ATTEMPTS:
                attempt = 0  # reset counter, continue at max backoff
