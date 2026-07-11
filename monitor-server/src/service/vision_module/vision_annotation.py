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
_COLOR_PERSON = (0, 255, 0)       # 绿色 — 人
_COLOR_OBJECT = (0, 0, 255)       # 红色 — 物品/危险物
_COLOR_TEXT = (255, 255, 255)     # 白色文字
_COLOR_LABEL_BG = (0, 0, 0)       # 文字背景黑色

_ENTITY_LABELS: dict[int, str] = {
    YOLOEntityType.PERSON: "Person",
    YOLOEntityType.CAR: "Car",
    YOLOEntityType.TRUCK: "Truck",
    YOLOEntityType.BUS: "Bus",
    YOLOEntityType.MOTORCYCLE: "Moto",
    YOLOEntityType.BICYCLE: "Bike",
    YOLOEntityType.DOG: "Dog",
    YOLOEntityType.CAT: "Cat",
    YOLOEntityType.BIRD: "Bird",
    YOLOEntityType.BACKPACK: "Bag",
    YOLOEntityType.SUITCASE: "Case",
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
    if labels:
        _face_labels = {int(k): v for k, v in labels.items()}


async def _on_fence_event(payload: dict) -> None:
    """订阅 FENCE topic，更新围栏标签映射。"""
    global _fence_labels
    fences: list[dict] = payload.get("fences", [])
    if fences:
        _fence_labels = {
            f["track_id"]: f"Fence-{f.get('fence_id', '?')}"
            for f in fences if "track_id" in f
        }


async def _on_action_event(payload: dict) -> None:
    """订阅 ACTION topic，更新动作标签映射。"""
    global _action_labels
    actions: list[dict] = payload.get("actions", [])
    if actions:
        _action_labels = {
            a["track_id"]: f"Action-{a.get('action_type_id', '?')}"
            for a in actions if "track_id" in a
        }


# 启动时注册订阅
import asyncio as _asyncio
try:
    loop = _asyncio.get_running_loop()
    loop.create_task(event_bus.subscribe(FACE, _on_face_event))
    loop.create_task(event_bus.subscribe(FENCE, _on_fence_event))
    loop.create_task(event_bus.subscribe(ACTION, _on_action_event))
except RuntimeError:
    pass  # 无运行中的 event loop（如测试导入）


def _bbox_color(entity_type_id: int | None) -> tuple[int, int, int]:
    """实体类型 → 框颜色。PERSON 绿色，其余红色。"""
    if entity_type_id == YOLOEntityType.PERSON:
        return _COLOR_PERSON
    return _COLOR_OBJECT


def draw_detections(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """在帧上绘制 YOLO 实体框和标签。返回新帧（不修改原帧）。"""
    annotated = frame.copy()

    for det in detections:
        if det.entity_type_id is None:
            continue
        x1, y1, x2, y2 = [int(v) for v in det.bbox]
        color = _bbox_color(det.entity_type_id)
        label = _ENTITY_LABELS.get(det.entity_type_id, f"#{det.entity_type_id}")
        if det.label_suffix:
            label = f"{label} {det.label_suffix}"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        _draw_label(annotated, label, x1, y1 - 10, color)

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


# late import after defining _bbox_color
import cv2
