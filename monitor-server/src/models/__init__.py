"""SQLAlchemy 模型包 —— 导入所有模型以便 Base.metadata.create_all 自动建表。

注意：Part A 模型变更（Node.is_connected/last_seen, VideoDevice/AudioDevice.streaming,
联合唯一约束, MonitorView.audio_id NOT NULL）需在对应模型文件中实现后，
Base.metadata.create_all 才会覆盖新字段 + 新约束。
"""

from .node import Node
from .video_device import VideoDevice
from .audio_device import AudioDevice
from .monitor_view import MonitorView
from .electronic_fence import ElectronicFence
from .fence_event_type import FenceEventType
from .entity_type import EntityType
from .action_type import ActionType
from .sound_type import SoundType
from .named_person import NamedPerson
from .alert_group import AlertGroup
from .exception import ExceptionDef, exception_entities, exception_actions, exception_sounds
from .response_action import ResponseAction, alert_group_responses
from .situation_event import SituationEvent
from .alert_review import AlertReview
from .face_recognition_result import FaceRecognitionResult
from .recording import Recording
from .log_entry import LogEntry
from .user import User
from .escalation_log import EscalationLog

__all__ = [
    "Node",
    "VideoDevice",
    "AudioDevice",
    "MonitorView",
    "ElectronicFence",
    "FenceEventType",
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
    "AlertReview",
    "FaceRecognitionResult",
    "Recording",
    "LogEntry",
    "User",
    "EscalationLog",
]
