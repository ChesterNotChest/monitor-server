"""计算机视觉管线——vision_module 内部逻辑包。

vision_* — 视频/音频分析子模块
vision_event_bus / vision_pipeline — 基础设施

Usage::

    from src.service.vision_module.vision_pipeline import AIPipeline
    from src.service.vision_module.vision_event_bus import event_bus
"""

from src.service.vision_module.vision_event_bus import event_bus, ENTITY, ACTION, SOUND, FACE, FENCE, RECORDING
from src.service.vision_module.video_ai_processor import VideoAIProcessor, register_video_ai_hooks

__all__ = [
    "VideoAIProcessor",
    "register_video_ai_hooks",
    "event_bus",
    "ENTITY",
    "ACTION",
    "SOUND",
    "FACE",
    "FENCE",
    "RECORDING",
]
