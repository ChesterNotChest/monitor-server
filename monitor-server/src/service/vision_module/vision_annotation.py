"""标注叠加——OpenCV 在检测结果上画框、标签。

标注内容：
  - YOLO 实体框（绿色 person / 红色 knife 等）
  - 人脸标签（订阅 EventBus FACE topic 获取 {track_id: label} 映射）
  - 时间戳由 Node 侧 drawtext 烧录
"""

from __future__ import annotations

import logging
import time as _time

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

# ── ActiveSignals — Pipeline 每帧提取的枚举信号快照 ──

from dataclasses import dataclass, field


@dataclass
class ActiveSignals:
    """一帧内所有 AI 检测的整数 ID 集合 — AlertEngine 告警匹配的单一数据源。

    全部为存在性集合 — 只关心"画面里有没有"，不关心中"哪个 track 引起的"。
    引用替换（非 mutate）确保无锁线程安全。
    """
    entity_type_ids: frozenset[int] = field(default_factory=frozenset)
    action_type_ids: frozenset[int] = field(default_factory=frozenset)
    sound_type_ids: frozenset[int] = field(default_factory=frozenset)
    face_result_ids: frozenset[int] = field(default_factory=frozenset)
    fence_result_ids: frozenset[int] = field(default_factory=frozenset)

    EMPTY: "ActiveSignals" = field(init=False, repr=False, default=None)

    @classmethod
    def empty(cls) -> "ActiveSignals":
        if cls.EMPTY is None:
            cls.EMPTY = cls()
        return cls.EMPTY


ActiveSignals.EMPTY = ActiveSignals()

# 检查"无信号"
_ACTIVE_SIGNALS = ActiveSignals.empty()

# 全局 ID 缓存 — 引用替换策略（GIL 下 set 引用赋值原子，无需显式锁）
_active_action_type_ids: frozenset[int] = frozenset()
_active_action_ids_updated_at: float = 0.0
_active_sound_type_ids: frozenset[int] = frozenset()
_active_sound_ids_updated_at: float = 0.0

# 信号 TTL（秒）—— 与 AlertEngine ALERT_EVENT_TTL 对齐
_SIGNAL_TTL: float = 5.0


def get_active_signals(
    entity_type_ids: frozenset[int] | None = None,
) -> ActiveSignals:
    """从全局缓存提取当前帧的枚举信号快照。

    - entity_type_ids: 调用方从当前帧 detections 提取后传入
    - action_type_ids: 读取 _active_action_type_ids（跨帧+TTL, SlowFast 结果按批产出）
    - sound_type_ids: 读取 _active_sound_type_ids（跨帧+TTL, YAMNet 持续产出）
    - face_result_ids: 从 _face_labels 推导 Stranger 存在性
    - fence_result_ids: 从 _fence_labels 推导 ENTERED 存在性

    所有字段使用 frozenset——引用替换保证无锁线程安全。
    """
    if entity_type_ids is None:
        entity_type_ids = frozenset()

    # 动作 TTL 检查（SlowFast 推理是批处理，结果跨帧保持）
    action_ids: frozenset[int]
    if _active_action_ids_updated_at > 0 and (
        _time.time() - _active_action_ids_updated_at < _SIGNAL_TTL
    ):
        action_ids = _active_action_type_ids
    else:
        action_ids = frozenset()

    # 声音 TTL 检查
    sound_ids: frozenset[int]
    if _active_sound_ids_updated_at > 0 and (
        _time.time() - _active_sound_ids_updated_at < _SIGNAL_TTL
    ):
        sound_ids = _active_sound_type_ids
    else:
        sound_ids = frozenset()

    # Face: Stranger/Spoof → 对应的 face_result_ids
    from src.constants import FaceRecognitionResult
    face_ids_set: set[int] = set()
    for v in _face_labels.values():
        if v == "Stranger":
            face_ids_set.add(FaceRecognitionResult.STRANGER)
        elif v == "Spoof":
            face_ids_set.add(FaceRecognitionResult.SPOOF)
    face_ids = frozenset(face_ids_set)

    # Fence: 解析 label 后缀提取结果类型
    from src.constants import FenceEventResult
    fence_ids_set: set[int] = set()
    for label in _fence_labels.values():
        if ":TOO_CLOSE" in label:
            fence_ids_set.add(FenceEventResult.TOO_CLOSE)
        elif ":IN" in label:
            fence_ids_set.add(FenceEventResult.ENTERED)
        else:
            # 向后兼容旧格式 "Fence-{id}"
            fence_ids_set.add(FenceEventResult.ENTERED)
    fence_ids = frozenset(fence_ids_set)

    return ActiveSignals(
        entity_type_ids=entity_type_ids,
        action_type_ids=action_ids,
        sound_type_ids=sound_ids,
        face_result_ids=face_ids,
        fence_result_ids=fence_ids,
    )


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
    """订阅 FENCE topic，更新围栏标签映射（支持 TOO_CLOSE）。"""
    global _fence_labels
    fences: list[dict] = payload.get("fences", [])
    logger.info("[FenceSub] called, fences=%s", len(fences))
    for f in fences:
        tid = f.get("track_id")
        if tid is None:
            continue
        entered = f.get("entered", False)
        result = f.get("result", "ENTERED")
        fid = f.get("fence_id", "?")
        if entered:
            suffix = ":TOO_CLOSE" if result == "TOO_CLOSE" else ":IN"
            _fence_labels[tid] = f"Fence-{fid}{suffix}"
        else:
            _fence_labels.pop(tid, None)


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
    fence_expanded_polygons: list[list[tuple[float, float]]] | None = None,
) -> np.ndarray:
    """Draw Part B tracking, face, action, and fence state on a frame."""

    annotated = frame.copy()
    face_labels = face_labels or {}
    action_labels = action_labels or {}
    fence_labels = fence_labels or {}

    if fence_expanded_polygons:
        for polygon in fence_expanded_polygons:
            points = np.array(polygon, dtype=np.int32)
            if len(points) >= 3:
                cv2.polylines(annotated, [points], isClosed=True, color=(80, 80, 255), thickness=1, lineType=cv2.LINE_AA)

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
    expanded: list[list[tuple[float, float]]] | None = None,
) -> np.ndarray:
    """在帧上绘制围栏多边形（橙色填充 + 边界线）+ 安全距离扩展框（细红线）。"""
    import cv2
    annotated = frame.copy()
    overlay = annotated.copy()
    for coords in polygons:
        pts = np.array([(int(x), int(y)) for x, y in coords], dtype=np.int32)
        if len(pts) >= 3:
            cv2.fillPoly(overlay, [pts], _COLOR_FENCE)
    cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, dst=annotated)

    if expanded:
        for coords in expanded:
            pts = np.array([(int(x), int(y)) for x, y in coords], dtype=np.int32)
            if len(pts) >= 3:
                cv2.polylines(annotated, [pts], isClosed=True, color=(80, 80, 255), thickness=1, lineType=cv2.LINE_AA)
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
