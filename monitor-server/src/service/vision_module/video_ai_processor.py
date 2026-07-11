"""Part B video AI processor hooked into the frame pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy.orm import Session

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
        self.slowfast_runner = SlowFastRunner()
        self.fence_engine = FenceEngine(view_id=view_id, db=db)

    async def process_frame(self, ctx: "FrameContext") -> None:
        tracks = self.tracker.update(ctx.detections)
        ctx.tracks = tracks
        if not tracks:
            return

        await self.face_recognizer.recognize_and_publish(ctx.frame, tracks, ctx.view_id)
        # 绕过事件总线直接更新全局标签（事件总线订阅在模块导入时序中有竞态）
        import logging as _logging
        from src.service.vision_module.vision_annotation import (
            _face_labels as _fl, _fence_labels as _fel, _action_labels as _al,
        )
        face_labels = self.face_recognizer.get_face_labels()
        if face_labels:
            _logging.getLogger(__name__).info("[Direct] updating _face_labels: %s", face_labels)
        _fl.clear(); _fl.update(face_labels)
        await self.fence_engine.check_and_publish(tracks, ctx.timestamp)

        for track in tracks:
            crop = _crop(ctx.frame, track)
            if crop is None:
                continue
            await self.slowfast_runner.enqueue_and_publish(track.track_id, crop, ctx.view_id)


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
