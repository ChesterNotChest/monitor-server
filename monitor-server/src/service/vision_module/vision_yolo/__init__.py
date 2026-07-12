"""YOLO11n 目标检测——video 管线的线性前置。

产出 EntityType 枚举事件。
"""

from src.service.vision_module.vision_yolo.detector import YoloDetector, Detection, YoloState

__all__ = ["YoloDetector", "Detection", "YoloState"]
