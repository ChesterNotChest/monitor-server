"""Part B video AI processor hooked into the frame pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy.orm import Session

from src.constants import SlowFastActionType
from src.service.vision_module.vision_face import FaceRecognizer
from src.service.vision_module.vision_fence import FenceEngine
from src.service.vision_module.vision_slowfast import SlowFastRunner
from src.service.vision_module.vision_tracking import ByteTracker
from src.service.vision_module.vision_types import Track

if TYPE_CHECKING:
    from src.service.vision_module.vision_pipeline import FrameContext


class VideoAIProcessor:
    """Wire Part B modules as one ``FrameContext`` hook."""

    def __init__(self, view_id: int, db: Session | None = None) -> None:
        self.view_id = view_id
        self.tracker = ByteTracker()
        self.face_recognizer = FaceRecognizer(db=db)
        self.slowfast_runner = SlowFastRunner(
            enable_real_kinetics=True, enable_real_ava=True, ava_confidence_threshold=0.3,
        )
        self.fence_engine = FenceEngine(view_id=view_id, db=db)

    async def process_frame(self, ctx: "FrameContext") -> None:
        tracks = self.tracker.update(ctx.detections)
        ctx.tracks = tracks
        if not tracks:
            return

        await self.face_recognizer.recognize_and_publish(ctx.frame, tracks, ctx.view_id)
        # ⚠️ 绕过事件总线直接更新全局标签（FACE + ACTION）
        # 事件总线订阅 create_task 有时静默失败，详见 vision_annotation.py:84-94 注释
        import logging as _logging
        from src.service.vision_module.vision_annotation import (
            _face_labels as _fl, _action_labels as _al,
        )
        face_labels = self.face_recognizer.get_face_labels()
        if face_labels:
            _logging.getLogger(__name__).info("[Direct] Face labels: %s", face_labels)
        _fl.update(face_labels)  # 增量更新，不清空已有标签

        action_results: list = []
        for track in tracks:
            crop = _crop_padded(ctx.frame, track, pad=0.3)
            if crop is None:
                continue
            results = await self.slowfast_runner.enqueue_and_publish(track.track_id, crop, ctx.view_id)
            action_results.extend(results)
        if action_results:
            # 同 track 多模型竞争 → 取最高置信度；不清空已有标签（增量更新）
            best: dict[int, tuple[float, str]] = {}
            for r in action_results:
                name = _action_type_name(r.action_type_id)
                if r.track_id not in best or r.confidence > best[r.track_id][0]:
                    best[r.track_id] = (r.confidence, name)
            _al.update({tid: name for tid, (_, name) in best.items()})
            _logging.getLogger(__name__).info("[Direct] Action labels: %s", dict(_al))

        await self.fence_engine.check_and_publish(tracks, ctx.timestamp)


def register_video_ai_hooks(
    pipeline: object,
    view_id: int,
    db: Session | None = None,
) -> VideoAIProcessor:
    """Create Part B processor and register it on an AIPipeline-like object."""

    processor = VideoAIProcessor(view_id=view_id, db=db)
    pipeline.register_frame_hook(processor.process_frame)  # type: ignore[attr-defined]
    return processor


def _crop(frame: np.ndarray, track: Track) -> np.ndarray | None:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in track.bbox]
    x1 = max(0, min(width, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height, y1))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def _crop_padded(frame: np.ndarray, track: Track, pad: float = 0.3) -> np.ndarray | None:
    """Crop person region with padding for action recognition context."""
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in track.bbox]
    bw, bh = x2 - x1, y2 - y1
    x1 -= bw * pad; x2 += bw * pad
    y1 -= bh * pad; y2 += bh * pad
    x1 = max(0, int(round(x1))); x2 = min(width, int(round(x2)))
    y1 = max(0, int(round(y1))); y2 = min(height, int(round(y2)))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def _action_type_name(action_type_id: int) -> str:
    """Map action_type_id to human-readable label."""
    try:
        return SlowFastActionType(action_type_id).name.capitalize()
    except ValueError:
        return f"Action-{action_type_id}"
