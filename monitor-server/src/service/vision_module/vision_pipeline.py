"""AI Pipeline 调度器——模块对接协议与主循环。

FrameContext 是所有帧处理模块的统一数据契约。
AIPipeline 管理模块注册、主循环启停、异常隔离。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

import numpy as np

from src.config import settings
from src.service.vision_module.vision_frame_reader import FrameReader, FrameReaderState
from src.service.vision_module.vision_yolo.detector import YoloDetector, Detection, YoloState
from src.service.vision_module.vision_annotation import draw_detections, draw_part_b_overlay
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

        while self._running:
            success, frame, ts, fid = self._reader.read()
            if not success:
                if self._reader.state == FrameReaderState.ERROR:
                    logger.error("FrameReader in ERROR state — stopping pipeline")
                    break
                continue  # 断流重连中

            # 首帧启动 FFmpeg merge
            if not merge_started:
                h, w = frame.shape[:2] if frame is not None else (480, 640)
                fps = int(self._reader.fps or settings.FPS_TARGET)
                self._merge_proc = await start_stream_merge(
                    view_id, w, h, fps, audio_id, audio_name,
                )
                if self._merge_proc is None:
                    logger.error("Failed to start stream merge — stopping pipeline")
                    break
                merge_started = True

            # YOLO 检测
            detections = await self._yolo.detect_and_publish(frame, view_id)

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

            # 标注叠加
            annotated = draw_detections(frame, detections)
            draw_part_b_overlay(frame, ctx.tracks if ctx.tracks else [])

            # 推流
            if self._merge_proc:
                await push_frame(self._merge_proc, annotated)

            # 录制：每帧推入环形缓冲区
            from src.service import replay_task
            replay_task.push_frame(view_id, annotated.tobytes())

        logger.info("Pipeline main loop exited for view_id=%d", view_id)
