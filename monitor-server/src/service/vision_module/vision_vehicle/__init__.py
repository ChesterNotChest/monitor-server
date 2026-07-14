"""Vehicle detection bypass — 车辆检测旁路处理器。

独立的 Frame Hook：蓝色框标注、IoU 去重、累计统计。
与 Part B 的 Person 管线完全解耦。
"""

from .processor import VehicleProcessor, VehicleStats

__all__ = ["VehicleProcessor", "VehicleStats"]
