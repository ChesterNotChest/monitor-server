"""数据仓库层 —— 统一导出所有 Repository 类。"""

from .base import BaseRepo
from .node_repo import NodeRepo
from .video_device_repo import VideoDeviceRepo
from .audio_device_repo import AudioDeviceRepo
from .monitor_view_repo import MonitorViewRepo
from .electronic_fence_repo import ElectronicFenceRepo
from .entity_type_repo import EntityTypeRepo
from .action_type_repo import ActionTypeRepo
from .sound_type_repo import SoundTypeRepo

# 组 B 将在后续补充: NamedPersonRepo, AlertGroupRepo, ExceptionDefRepo, ResponseActionRepo, SituationEventRepo

__all__ = [
    "BaseRepo",
    "NodeRepo",
    "VideoDeviceRepo",
    "AudioDeviceRepo",
    "MonitorViewRepo",
    "ElectronicFenceRepo",
    "EntityTypeRepo",
    "ActionTypeRepo",
    "SoundTypeRepo",
]
