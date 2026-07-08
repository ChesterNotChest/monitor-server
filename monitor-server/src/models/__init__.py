"""SQLAlchemy 模型包 —— 导入所有模型以便 Base.metadata.create_all 自动建表。"""

from .node import Node
from .video_device import VideoDevice
from .audio_device import AudioDevice
from .monitor_view import MonitorView
from .electronic_fence import ElectronicFence
from .entity_type import EntityType
from .action_type import ActionType
from .sound_type import SoundType
from .named_person import NamedPerson
from .alert_group import AlertGroup
from .exception import ExceptionDef, exception_entities, exception_actions, exception_sounds
from .response_action import ResponseAction, alert_group_responses
from .situation_event import SituationEvent

__all__ = [
    "Node",
    "VideoDevice",
    "AudioDevice",
    "MonitorView",
    "ElectronicFence",
    "EntityType",
    "ActionType",
    "SoundType",
    "NamedPerson",
    "AlertGroup",
    "ExceptionDef",
    "exception_entities",
    "exception_actions",
    "exception_sounds",
    "ResponseAction",
    "alert_group_responses",
    "SituationEvent",
]
