"""YOLO11 目标检测——video 管线的线性前置。

加载 yolo11n.pt（COCO 预训练），每帧推理，产出 EntityType 枚举事件。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import os
import numpy as np

# ── 必须在 ultralytics import 之前禁用 CUDA ─────────────────
# run.py 启动时已根据 YOLO_DEVICE 设置 CUDA_VISIBLE_DEVICES。
# 这里用 setdefault 兜底测试等不走 run.py 的场景。
_yolo_device = os.environ.get("YOLO_DEVICE", "cpu")
if _yolo_device in ("", "cpu"):
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from ultralytics import YOLO

from src.config import settings
from src.constants import YOLOEntityType
from src.service.vision_module.vision_event_bus import ENTITY, event_bus

logger = logging.getLogger(__name__)

# ── COCO class_id → EntityType 映射（12 类） ───
_COCO_TO_ENTITY: dict[int, int] = {
    0:  YOLOEntityType.PERSON,       # person
    2:  YOLOEntityType.CAR,          # car
    7:  YOLOEntityType.TRUCK,        # truck
    5:  YOLOEntityType.BUS,          # bus
    3:  YOLOEntityType.MOTORCYCLE,   # motorcycle
    1:  YOLOEntityType.BICYCLE,      # bicycle
    16: YOLOEntityType.DOG,          # dog
    15: YOLOEntityType.CAT,          # cat
    14: YOLOEntityType.BIRD,         # bird
    24: YOLOEntityType.BACKPACK,     # backpack
    28: YOLOEntityType.SUITCASE,     # suitcase
    43: YOLOEntityType.KNIFE,        # knife
}


class YoloState(Enum):
    IDLE = auto()
    ACTIVE = auto()
    ERROR = auto()


@dataclass
class Detection:
    """单条 YOLO 检测结果。"""
    bbox: list[float]       # [x1, y1, x2, y2] 像素坐标
    class_id: int            # 原始 COCO class_id
    confidence: float        # 置信度 0-1
    entity_type_id: int | None  # 映射后的 EntityType id，非关注类为 None
    label_suffix: str | None = None  # 附加标签（Track ID / Face / Action / Fence）


class YoloDetector:
    """YOLO11n 目标检测器。"""

    def __init__(self) -> None:
        self._model: YOLO | None = None
        self._state = YoloState.IDLE
        self._consecutive_failures: int = 0

    @property
    def state(self) -> YoloState:
        return self._state

    # ── Lifecycle ──────────────────────────────

    def load(self) -> bool:
        """加载 YOLO 模型。"""
        model_path = Path(settings.YOLO_MODEL_PATH)
        if not model_path.exists():
            logger.error("YOLO model not found: %s", model_path)
            self._state = YoloState.ERROR
            return False
        try:
            self._model = YOLO(str(model_path), task="detect")
            _device = settings.YOLO_DEVICE
            if _device.isdigit():
                _device = int(_device)  # PyTorch 需要 int 而非 "0" 字符串
            self._model.to(_device)
            # 预热推理
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self._model(dummy, verbose=False)
            self._state = YoloState.ACTIVE
            logger.info("YOLO model loaded from %s", model_path)
            return True
        except Exception:
            logger.exception("Failed to load YOLO model")
            self._state = YoloState.ERROR
            return False

    # ── Inference ──────────────────────────────

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """对单帧做目标检测。

        Returns:
            Detection 列表——仅包含置信度 > YOLO_CONFIDENCE 且在 12 类映射中的检测。
        """
        if self._state != YoloState.ACTIVE or self._model is None:
            return []

        try:
            results = self._model(frame, verbose=False)
            self._consecutive_failures = 0
        except Exception:
            self._consecutive_failures += 1
            logger.exception("YOLO inference failed (consecutive=%d)", self._consecutive_failures)
            if self._consecutive_failures > 10:
                self._state = YoloState.ERROR
            return []

        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes.xyxy.cpu().numpy()        # (N, 4)
            classes = result.boxes.cls.cpu().numpy().astype(int)  # (N,)
            confs = result.boxes.conf.cpu().numpy()         # (N,)

            for box, cls_id, conf in zip(boxes, classes, confs):
                if conf < settings.YOLO_CONFIDENCE:
                    continue
                entity_id = _COCO_TO_ENTITY.get(int(cls_id))
                detections.append(Detection(
                    bbox=box.tolist(),
                    class_id=int(cls_id),
                    confidence=float(conf),
                    entity_type_id=entity_id,
                ))

        return detections

    async def detect_and_publish(self, frame: np.ndarray, view_id: int) -> list[Detection]:
        """检测并发布 EntityType 事件到 EventBus。"""
        detections = self.detect(frame)
        entities = [
            {"entity_type_id": d.entity_type_id, "bbox": d.bbox, "confidence": d.confidence}
            for d in detections if d.entity_type_id is not None
        ]
        if entities:
            await event_bus.publish(ENTITY, {"view_id": view_id, "entities": entities})
        return detections
