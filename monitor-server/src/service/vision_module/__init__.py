"""计算机视觉管线——vision_module 内部逻辑包。

vision_* — 视频/音频分析子模块
vision_event_bus / vision_pipeline — 基础设施

Usage::

    from src.service.vision_module.vision_pipeline import AIPipeline
    from src.service.vision_module.vision_event_bus import event_bus
"""

from src.service.vision_module.vision_pipeline import AIPipeline, FrameContext, Track, FrameHook
from src.service.vision_module.vision_event_bus import event_bus, ENTITY, ACTION, SOUND, FACE, FENCE, RECORDING

__all__ = [
    "AIPipeline",
    "FrameContext",
    "Track",
    "FrameHook",
    "event_bus",
    "ENTITY",
    "ACTION",
    "SOUND",
    "FACE",
    "FENCE",
    "RECORDING",
]
