"""标注叠加——OpenCV 在检测结果上画框、标签。

标注内容：
  - YOLO 实体框（绿色 person / 红色 knife 等）
  - 人脸标签（订阅 EventBus FACE topic 获取 {track_id: label} 映射）
  - 时间戳由 Node 侧 drawtext 烧录
"""

from __future__ import annotations

import logging

import numpy as np

from src.constants import YOLOEntityType
from src.service.vision_module.vision_event_bus import FACE, FENCE, ACTION, event_bus
from src.service.vision_module.vision_yolo.detector import Detection
from src.service.vision_module.vision_types import Track

logger = logging.getLogger(__name__)

# ── 配色方案 ──────────────────────────────────
_COLOR_NORMAL = (0, 255, 0)       # 绿色 — 正常
_COLOR_IMPORTANT = (0, 215, 255)  # 黄色 — 关注
_COLOR_DANGER = (0, 0, 255)       # 红色 — 危险
_COLOR_PERSON = (0, 255, 0)       # 绿色 — Person 检测框
_COLOR_TEXT = (255, 255, 255)     # 白色文字
_COLOR_LABEL_BG = (0, 0, 0)       # 文字背景黑色

_ENTITY_LABELS: dict[int, str] = {
    YOLOEntityType.PERSON: "Person",
    YOLOEntityType.KNIFE: "Knife",
}

# ── 当前帧的 Part B 标签（各模块产出后更新） ──
_face_labels: dict[int, str] = {}
_fence_labels: dict[int, str] = {}
_action_labels: dict[int, str] = {}


async def _on_face_event(payload: dict) -> None:
    """订阅 FACE topic，更新人脸标签映射。"""
    global _face_labels
    labels = payload.get("labels", {})
    logger.info("[FaceSub] called, labels=%s has_faces=%s", labels, payload.get("faces", "?")[:1])
    if labels:
        _face_labels = {int(k): v for k, v in labels.items()}
    else:
        logger.warning("[FaceSub] payload has no 'labels' key: %s", list(payload.keys()))


async def _on_fence_event(payload: dict) -> None:
    """订阅 FENCE topic，更新围栏标签映射。"""
    global _fence_labels
    fences: list[dict] = payload.get("fences", [])
    logger.info("[FenceSub] called, fences=%s", len(fences))
    if fences:
        _fence_labels = {
            f["track_id"]: f"Fence-{f.get('fence_id', '?')}"
            for f in fences if "track_id" in f
        }


async def _on_action_event(payload: dict) -> None:
    """订阅 ACTION topic，更新动作标签映射。"""
    global _action_labels
    actions: list[dict] = payload.get("actions", [])
    logger.info("[ActionSub] called, actions=%s", len(actions))
    if actions:
        _action_labels = {
            a["track_id"]: f"Action-{a.get('action_type_id', '?')}"
            for a in actions if "track_id" in a
        }


# 启动时注册订阅
# ⚠️ 已知问题 (2026-07-11): create_task(fire-and-forget) 创建的订阅任务
# 有时静默失败，导致 _on_*_event 从未被调用，标签 dict 始终为空。
# 当前绕过方案：video_ai_processor.py 的 process_frame() 中直接调用
# get_face_labels() 更新 _face_labels。事件总线方案留作后续修复。
import asyncio as _asyncio
try:
    loop = _asyncio.get_running_loop()
    loop.create_task(event_bus.subscribe(FACE, _on_face_event))
    loop.create_task(event_bus.subscribe(FENCE, _on_fence_event))
    loop.create_task(event_bus.subscribe(ACTION, _on_action_event))
except RuntimeError:
    pass  # 无运行中的 event loop（如测试导入）


def _alert_color(level: int) -> tuple[int, int, int]:
    """alert_level → 框颜色。0=绿 1=黄 2=红。"""
    if level >= 2:
        return _COLOR_DANGER
    if level == 1:
        return _COLOR_IMPORTANT
    return _COLOR_NORMAL


def draw_detections(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """在帧上绘制检测框和标签。

    三级着色：danger(红) > important(黄) > normal(绿)。
    label_suffix 为 None 的检测跳过（抑制的实体）。
    """
    annotated = frame.copy()
    drawn = 0

    for det in detections:
        if det.label_suffix is None:
            continue
        drawn += 1
        x1, y1, x2, y2 = [int(v) for v in det.bbox]
        color = _alert_color(det.alert_level)
        label = det.label_suffix

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        _draw_label(annotated, label, x1, y1 - 10, color)

    logger.info("[Draw] total=%d drawn=%d", len(detections), drawn)
    return annotated


def draw_face_labels(frame: np.ndarray, face_results: dict[int, str]) -> np.ndarray:
    """在帧上绘制人脸姓名/陌生人标签。

    face_results: {track_id: label} — label 为姓名或 "Stranger"。
    """
    # 人脸标签通过 _face_labels 全局缓存 + Person 框位置叠加
    # Face 模块产出 track_id → label 后通过 EventBus FACE topic 通知
    annotated = frame.copy()
    # 实际绘制由 Pipeline 主循环在拿到 YOLO person 框 + face_labels 后完成
    return annotated


def draw_part_b_overlay(
    frame: np.ndarray,
    tracks: list[Track],
    *,
    face_labels: dict[int, str] | None = None,
    action_labels: dict[int, str] | None = None,
    fence_labels: dict[int, str] | None = None,
    fence_polygons: list[list[tuple[float, float]]] | None = None,
) -> np.ndarray:
    """Draw Part B tracking, face, action, and fence state on a frame."""

    annotated = frame.copy()
    face_labels = face_labels or {}
    action_labels = action_labels or {}
    fence_labels = fence_labels or {}

    if fence_polygons:
        for polygon in fence_polygons:
            points = np.array(polygon, dtype=np.int32)
            if len(points) >= 3:
                cv2.polylines(annotated, [points], isClosed=True, color=(255, 255, 0), thickness=2)

    for track in tracks:
        x1, y1, x2, y2 = [int(round(value)) for value in track.bbox]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), _COLOR_PERSON, 2)
        labels = [f"ID {track.track_id}"]

        face = face_labels.get(track.track_id)
        if face:
            labels.append(f"Face: {face}")

        action = action_labels.get(track.track_id)
        if action:
            labels.append(f"Action: {action}")

        fence = fence_labels.get(track.track_id)
        if fence:
            labels.append(f"Fence: {fence}")

        for index, label in enumerate(labels):
            _draw_label(annotated, label, x1, y1 - 10 - index * 20, _COLOR_PERSON)

    return annotated


def _draw_label(
    img: np.ndarray, text: str, x: int, y: int, color: tuple[int, int, int],
) -> None:
    """在框上方绘制带背景色的标签文字。"""
    import cv2
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y = max(y, th + 4)
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 4, y), _COLOR_LABEL_BG, -1)
    cv2.putText(img, text, (x + 2, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


_COLOR_ACTION_REGION = (0, 255, 128)  # 浅绿半透明 — SlowFast padded crop 范围


def draw_action_regions(
    frame: np.ndarray,
    regions: dict[int, tuple[int, int, int, int]],
) -> np.ndarray:
    """在帧上绘制 SlowFast padded crop 区域（淡色虚线框）。"""
    import cv2
    annotated = frame.copy()
    overlay = annotated.copy()
    for x1, y1, x2, y2 in regions.values():
        cv2.rectangle(overlay, (x1, y1), (x2, y2), _COLOR_ACTION_REGION, 1)
    # 半透明叠加
    cv2.addWeighted(overlay, 0.35, annotated, 0.65, 0, dst=annotated)
    return annotated


_COLOR_FENCE = (0, 165, 255)  # 橙色 — 围栏边界


def draw_fence_polygons(
    frame: np.ndarray,
    polygons: list[list[tuple[float, float]]],
) -> np.ndarray:
    """在帧上绘制围栏多边形（橙色填充 + 边界线）。"""
    import cv2
    annotated = frame.copy()
    overlay = annotated.copy()
    for coords in polygons:
        pts = np.array([(int(x), int(y)) for x, y in coords], dtype=np.int32)
        if len(pts) >= 3:
            cv2.fillPoly(overlay, [pts], _COLOR_FENCE)
    cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, dst=annotated)
    return annotated


# ── 音频事件显示（左下角持久化） ──────────────

_sound_label: str | None = None
_sound_time: float = 0.0


def set_sound_label(label: str | None) -> None:
    """设置当前音频事件标签。label=None 则清除。"""
    import time as _time
    global _sound_label, _sound_time
    _sound_label = label
    _sound_time = _time.time() if label else 0.0


def draw_server_timestamp(frame: np.ndarray) -> np.ndarray:
    """左上角叠加 Server 处理时间戳（黄色），与 Node 右下角 drawtext 对比 = 端到端延迟。"""
    import cv2 as _cv2
    import time as _time
    ts = _time.strftime("%H:%M:%S")
    (tw, th), _ = _cv2.getTextSize(ts, _cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    _cv2.rectangle(frame, (4, 4), (tw + 10, th + 10), (0, 0, 0), -1)
    _cv2.putText(frame, ts, (8, th + 6), _cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    return frame


def draw_sound_overlay(frame: np.ndarray) -> np.ndarray:
    """左下角音频检测标签（红字），格式 ``SOUND: Gunshot (3s ago)``。"""
    import cv2 as _cv2
    import time as _time
    global _sound_label, _sound_time
    if _sound_label is None:
        return frame
    elapsed = _time.time() - _sound_time if _sound_time > 0 else 0
    text = f"SOUND: {_sound_label} ({elapsed:.0f}s ago)"
    h, w = frame.shape[:2]
    (tw, th), _ = _cv2.getTextSize(text, _cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    overlay = frame.copy()
    _cv2.rectangle(overlay, (10, h - th - 16), (tw + 20, h - 4), (0, 0, 0), -1)
    _cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, dst=frame)
    _cv2.putText(frame, text, (16, h - 10), _cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return frame


# late import after defining _bbox_color
import cv2
