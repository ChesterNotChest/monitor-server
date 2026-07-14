"""Part B video AI processor hooked into the frame pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy.orm import Session

from src.constants import SlowFastActionType, FenceEventResult
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
        # 预加载模型到 GPU——避免首帧推理时 CUDA 分配卡 YOLO
        self.slowfast_runner.load()
        self.fence_engine = FenceEngine(view_id=view_id, db=db)
        self._frame_count = 0  # 启动错峰计数器

    async def process_frame(self, ctx: "FrameContext") -> None:
        self._frame_count += 1
        tracks = self.tracker.update(ctx.detections)
        ctx.tracks = tracks
        # 围栏多边形每帧都设——不管有没有人
        polys = self.fence_engine.fence_polygons
        ctx.fence_polygons = polys
        ctx.fence_expanded_polygons = self.fence_engine.expanded_polygons
        import logging as _logging
        _slog = _logging.getLogger(__name__)
        if polys:
            _slog.info("[ProcFrame] fence_polygons: %d polygon(s)", len(polys))
        elif ctx.frame_id <= 3:
            _slog.info("[ProcFrame] fence_polygons is EMPTY (fence_engine._fences=%d)",
                        len(self.fence_engine._fences))

        if not tracks:
            # 无 track 时清空动作 ID 缓存
            import src.service.vision_module.vision_annotation as _van
            _van._active_action_type_ids[self.view_id] = frozenset()
            return

        # 启动错峰：前 2 帧只跑 tracker + fence，第 3 帧起开人脸，第 4 帧起开动作
        _WARMUP_FACE_START = 3
        _WARMUP_ACTION_START = 4

        if self._frame_count <= 5:
            _slog.info("[dbg] procFrame=%d tracks=%d", self._frame_count, len(tracks))

        if self._frame_count >= _WARMUP_FACE_START:
            await self.face_recognizer.recognize_and_publish(ctx.frame, tracks, ctx.view_id)
        # ⚠️ 绕过事件总线直接更新全局标签（FACE + ACTION）
        # 事件总线订阅 create_task 有时静默失败，详见 vision_annotation.py:84-94 注释
        import logging as _logging
        from src.service.vision_module.vision_annotation import (
            _face_labels as _fl, _action_labels as _al, _fence_labels as _fel,
        )
        face_labels = self.face_recognizer.get_face_labels()
        _prev_fl = dict(_fl)
        _fl.update(face_labels)  # 增量更新，不清空已有标签
        # 只在标签变化时输出
        if _fl != _prev_fl and face_labels:
            _logging.getLogger(__name__).info("[Direct] Face labels: %s", face_labels)

        # SlowFast: enqueue + publish ACTION events (non-blocking)
        _MIN_BOX_AREA = 6400  # ~80×80
        ctx.action_regions = {}
        if self._frame_count >= _WARMUP_ACTION_START:
            for track in tracks:
                # 跳过 SPOOF（假脸不做动作检测）
                if face_labels.get(track.track_id) == "Spoof":
                    continue
                x1, y1, x2, y2 = track.bbox
                box_w, box_h = x2 - x1, y2 - y1
                if box_w * box_h < _MIN_BOX_AREA:
                    continue  # 人太小 → 不跑动作检测
                bbox = _padded_bbox(track.bbox, ctx.frame.shape[1], ctx.frame.shape[0], pad=0.3)
                if bbox is None:
                    continue
                ctx.action_regions[track.track_id] = bbox
                crop = _crop_padded(ctx.frame, track, pad=0.3)
                if crop is not None:
                    self.slowfast_runner.enqueue(track.track_id, crop)  # 同步，只入队不 publish
        action_results = self.slowfast_runner.collect_results() if self._frame_count >= _WARMUP_ACTION_START else []
        if action_results:
            # 置信度阈值: 低于此值的动作不进标签
            _MIN_CONF_DEFAULT = 0.55
            # 易漏检动作降低阈值（摔倒/躺着姿态变化小，模型置信度天然低）
            _MIN_CONF_PER_ACTION: dict[int, float] = {
                SlowFastActionType.FALLING: 0.35,
                SlowFastActionType.LYING_DOWN: 0.4,
            }
            # 同 track 多模型/多类合并 — 全部保留，管道分隔
            all_names: dict[int, set[str]] = {}
            for r in action_results:
                _min = _MIN_CONF_PER_ACTION.get(r.action_type_id, _MIN_CONF_DEFAULT)
                if r.confidence >= _min:
                    all_names.setdefault(r.track_id, set()).add(_action_type_name(r))
            _prev_al = dict(_al)
            _al.update({tid: "|".join(sorted(names)) for tid, names in all_names.items()})
            if _al != _prev_al:
                # 摘要: 每种动作的 track 数量
                summary: dict[str, int] = {}
                for v in _al.values():
                    for name in v.split("|"):
                        summary[name] = summary.get(name, 0) + 1
                _logging.getLogger(__name__).info("[Direct] Action summary: %s", summary)
            # 同步写入整数 ID 缓存（跨帧保留+TTL，引用替换无锁安全）
            import time as _t
            import src.service.vision_module.vision_annotation as _van
            _new_ids = frozenset(r.action_type_id for r in action_results
                                if r.confidence >= _MIN_CONF_PER_ACTION.get(r.action_type_id, _MIN_CONF_DEFAULT))
            _van._active_action_type_ids[self.view_id] = \
                _van._active_action_type_ids.get(self.view_id, frozenset()).union(_new_ids)
            _van._active_action_ids_updated_at[self.view_id] = _t.time()

        fence_events = await self.fence_engine.check_and_publish(tracks, ctx.timestamp)
        if fence_events:
            for e in fence_events:
                if e.entered:
                    suffix = ":TOO_CLOSE" if e.result == FenceEventResult.TOO_CLOSE else ":IN"
                    _fel[e.track_id] = f"Fence-{e.fence_id}{suffix}"
                else:
                    _fel.pop(e.track_id, None)  # 离开围栏：清除标签
        ctx.fence_polygons = self.fence_engine.fence_polygons
        ctx.fence_expanded_polygons = self.fence_engine.expanded_polygons


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


def _padded_bbox(bbox: list[float], frame_w: int, frame_h: int,
                  pad: float = 0.3) -> tuple[int, int, int, int] | None:
    """Compute padded bbox coords (no cropping)."""
    x1, y1, x2, y2 = [float(v) for v in bbox]
    bw, bh = x2 - x1, y2 - y1
    x1 -= bw * pad; x2 += bw * pad
    y1 -= bh * pad; y2 += bh * pad
    x1 = max(0, int(round(x1))); x2 = min(frame_w, int(round(x2)))
    y1 = max(0, int(round(y1))); y2 = min(frame_h, int(round(y2)))
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def _crop_padded(frame: np.ndarray, track: Track, pad: float = 0.3) -> np.ndarray | None:
    """Crop person region with padding for action recognition context."""
    height, width = frame.shape[:2]
    bbox = _padded_bbox(track.bbox, width, height, pad)
    if bbox is None:
        return None
    x1, y1, x2, y2 = bbox
    return frame[y1:y2, x1:x2]


def _action_type_name(r) -> str:
    """Map action result to human-readable label."""
    try:
        return SlowFastActionType(r.action_type_id).name.capitalize()
    except ValueError:
        return r.label.capitalize() if r.label else f"Action-{r.action_type_id}"
