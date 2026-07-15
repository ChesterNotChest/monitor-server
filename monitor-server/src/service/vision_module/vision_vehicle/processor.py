"""VehicleProcessor — 车辆检测旁路的 Frame Hook。

从 YOLO detections 中过滤 5 类车辆，蓝色框标注，网格哈希 + IoU 去重，累计统计。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cv2
import numpy as np

from src.constants import YOLOEntityType

if TYPE_CHECKING:
    from src.service.vision_module.vision_pipeline import FrameContext

logger = logging.getLogger(__name__)

# ── 车辆类别 id → 英文 key + 中文名 ──────────────────
_VEHICLE_CLASSES: dict[int, tuple[str, str]] = {
    YOLOEntityType.CAR:        ("car",        "轿车"),
    YOLOEntityType.TRUCK:      ("truck",      "卡车"),
    YOLOEntityType.BUS:        ("bus",        "公交车"),
    YOLOEntityType.MOTORCYCLE: ("motorcycle", "摩托车"),
    YOLOEntityType.BICYCLE:    ("bicycle",    "自行车"),
}

# ── 默认配置（可通过 settings 覆盖） ──────────────────
DEFAULT_VEHICLE_CONFIDENCE = 0.4
DEFAULT_VEHICLE_IOU_THRESHOLD = 0.5
DEFAULT_VEHICLE_DEDUP_FRAMES = 30

# ── 绘制常量 ─────────────────────────────────────────
_VEHICLE_BOX_COLOR = (255, 0, 0)   # BGR 蓝色
_VEHICLE_BOX_THICKNESS = 2
_VEHICLE_FONT = cv2.FONT_HERSHEY_SIMPLEX
_VEHICLE_FONT_SCALE = 0.5
_VEHICLE_FONT_THICKNESS = 1
_GRID_SIZE = 16  # 去重网格划分


def _bbox_iou(a: list[float], b: list[float]) -> float:
    """两块区域之间的 IoU（[x1, y1, x2, y2]）。"""
    x_left = max(a[0], b[0])
    y_top = max(a[1], b[1])
    x_right = min(a[2], b[2])
    y_bottom = min(a[3], b[3])
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    inter = (x_right - x_left) * (y_bottom - y_top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter + 1e-6)


def _grid_cells(bbox: list[float], grid: int = _GRID_SIZE) -> set[int]:
    """返回 bbox 覆盖的网格单元索引（用于快速查找）。"""
    x1, y1, x2, y2 = bbox
    cells: set[int] = set()
    for gx in range(int(x1) // grid, int(x2) // grid + 1):
        for gy in range(int(y1) // grid, int(y2) // grid + 1):
            cells.add(gx * 1000 + gy)  # 简单二维 → 一维
    return cells


@dataclass
class VehicleStats:
    """车辆统计数据。"""
    total_unique: dict[str, int] = field(default_factory=lambda: {
        "car": 0, "truck": 0, "bus": 0, "motorcycle": 0, "bicycle": 0,
    })
    current_frame: dict[str, int] = field(default_factory=lambda: {
        "car": 0, "truck": 0, "bus": 0, "motorcycle": 0, "bicycle": 0,
    })
    fps: float = 0.0


class VehicleProcessor:
    """车辆检测旁路处理器。

    作为独立 Frame Hook 注册到 AIPipeline，与 VideoAIProcessor 完全解耦。
    """

    def __init__(
        self,
        confidence: float | None = None,
        iou_threshold: float | None = None,
        dedup_frames: int | None = None,
    ) -> None:
        try:
            from src.config import settings
            self._confidence = confidence if confidence is not None else settings.VEHICLE_CONFIDENCE
            self._iou_threshold = iou_threshold if iou_threshold is not None else settings.VEHICLE_IOU_THRESHOLD
            self._dedup_frames = dedup_frames if dedup_frames is not None else settings.VEHICLE_DEDUP_FRAMES
        except Exception:
            self._confidence = confidence or DEFAULT_VEHICLE_CONFIDENCE
            self._iou_threshold = iou_threshold or DEFAULT_VEHICLE_IOU_THRESHOLD
            self._dedup_frames = dedup_frames or DEFAULT_VEHICLE_DEDUP_FRAMES

        self._stats = VehicleStats()

        # 去重状态: class_key → {grid_cell → [(bbox, age_frames), ...]}
        self._seen: dict[str, dict[int, list[tuple[list[float], int]]]] = {}
        for key in self._stats.total_unique:
            self._seen[key] = {}

        self._frame_count: int = 0

    # ── Frame Hook ──────────────────────────────────

    async def process_frame(self, ctx: FrameContext) -> None:
        """处理当前帧：过滤车辆 detections → 去重 → 统计 → 填充 ctx.vehicle_detections。"""
        self._frame_count += 1

        # 0. 诊断：统计原始 YOLO 车辆检测置信度分布
        raw_vehicles = [
            d for d in ctx.detections
            if d.entity_type_id in _VEHICLE_CLASSES
        ]
        if raw_vehicles and self._frame_count % 30 == 0:
            confs = [d.confidence for d in raw_vehicles]
            confs.sort()
            below = sum(1 for c in confs if c < self._confidence)
            logger.info("[Vehicle] frame=%d raw_vehicles=%d below_%.2f=%d min=%.2f max=%.2f avg=%.2f",
                        self._frame_count, len(raw_vehicles), self._confidence,
                        below, min(confs), max(confs),
                        sum(confs) / len(confs) if confs else 0)

        # 1. 过滤车辆类 Detection
        vehicles = [
            d for d in ctx.detections
            if d.entity_type_id in _VEHICLE_CLASSES
            and d.confidence >= self._confidence
        ]
        if not vehicles:
            # 没有车辆，清空当前帧计数
            for key in self._stats.current_frame:
                self._stats.current_frame[key] = 0
            ctx.vehicle_detections = vehicles
            self._periodic_cleanup()
            return

        # 2. 当前帧去重 + 与历史记录去重
        current_frame_counts: dict[str, int] = {key: 0 for key in self._seen}
        new_vehicles: list = []  # 标记为 "new" 的 detection

        for det in vehicles:
            entity_id = det.entity_type_id
            if entity_id is None:
                continue
            key, _name = _VEHICLE_CLASSES[entity_id]
            cells = _grid_cells(det.bbox)

            is_new = True
            # 检查该类别在各网格中的历史记录
            for cell in cells:
                history = self._seen[key].get(cell, [])
                for hist_bbox, _age in history:
                    if _bbox_iou(det.bbox, hist_bbox) >= self._iou_threshold:
                        is_new = False
                        break
                if not is_new:
                    break

            if is_new:
                self._stats.total_unique[key] += 1
                new_vehicles.append(det)
                # 将新车辆加入所有覆盖网格的历史
                for cell in cells:
                    self._seen[key].setdefault(cell, []).append((det.bbox, 0))

            current_frame_counts[key] += 1

        # 3. 更新当前帧计数
        for key in self._stats.current_frame:
            self._stats.current_frame[key] = current_frame_counts.get(key, 0)

        # 4. 构建 label_suffix（仅标记为 new 的车辆用 "★新"，其余用类名）
        for det in vehicles:
            entity_id = det.entity_type_id
            if entity_id is None:
                continue
            _key, name = _VEHICLE_CLASSES[entity_id]
            det.label_suffix = name  # 所有车辆都有标签

        # 5. 填充 ctx
        ctx.vehicle_detections = vehicles

        self._periodic_cleanup()

    # ── Stats ───────────────────────────────────────

    def get_stats(self) -> VehicleStats:
        """返回当前统计数据快照。"""
        return self._stats

    # ── Internal ────────────────────────────────────

    def _periodic_cleanup(self) -> None:
        """每 N 帧清理一次过期的去重记录。"""
        if self._frame_count % self._dedup_frames != 0:
            return
        for key in list(self._seen):
            cleaned: dict[int, list[tuple[list[float], int]]] = {}
            for cell, records in self._seen[key].items():
                kept = [(b, age + self._dedup_frames) for b, age in records if age < self._dedup_frames * 2]
                if kept:
                    cleaned[cell] = kept
            self._seen[key] = cleaned


def draw_vehicle_detections(frame: np.ndarray, vehicle_detections: list) -> np.ndarray:
    """在帧上绘制蓝色车辆检测框和类型标签。

    Args:
        frame: BGR24 numpy 帧（可能已被其他绘制函数修改）
        vehicle_detections: VehicleProcessor 处理后的 Detection 列表

    Returns:
        绘制后的帧（原地修改 + 返回引用）
    """
    drawn = 0
    for det in vehicle_detections:
        if det.label_suffix is None:
            continue
        x1, y1, x2, y2 = [int(v) for v in det.bbox]
        label = det.label_suffix

        cv2.rectangle(frame, (x1, y1), (x2, y2), _VEHICLE_BOX_COLOR, _VEHICLE_BOX_THICKNESS)

        # 标签背景
        (tw, th), bl = cv2.getTextSize(label, _VEHICLE_FONT, _VEHICLE_FONT_SCALE, _VEHICLE_FONT_THICKNESS)
        label_y = y1 - 10 if y1 - 10 > th else y1 + th + 4
        cv2.rectangle(frame, (x1, label_y - th - 2), (x1 + tw, label_y + 2),
                      _VEHICLE_BOX_COLOR, -1)
        cv2.putText(frame, label, (x1, label_y), _VEHICLE_FONT,
                    _VEHICLE_FONT_SCALE, (255, 255, 255), _VEHICLE_FONT_THICKNESS)
        drawn += 1

    if drawn:
        logger.debug("[Vehicle] drew %d vehicle boxes", drawn)
    return frame
