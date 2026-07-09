"""HTTP Schema 包 —— REST 请求/响应 Pydantic 模型。"""

from .named_person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from .node_schema import AudioDeviceResponse, NodeResponse, VideoDeviceResponse
from .view_schema import ViewCreateRequest, ViewResponse
from .enum_types import EnumTypeCreate, EnumTypeUpdate, EnumTypeResponse
from .alert import (
    ResponseActionCreate,
    ResponseActionUpdate,
    ResponseActionResponse,
    AlertGroupCreate,
    AlertGroupUpdate,
    AlertGroupResponse,
    ResponseBindRequest,
)
from .exception import (
    ExceptionCreate,
    ExceptionUpdate,
    ExceptionResponse,
    ExceptionListResponse,
    EntityBindRequest,
    ActionBindRequest,
    SoundBindRequest,
)
from .event import (
    EventResponse,
    EventListResponse,
    ExceptionStatsItem,
    TrendItem,
)

__all__ = [
    "PersonCreate",
    "PersonUpdate",
    "PersonResponse",
    "PersonListResponse",
    "AudioDeviceResponse",
    "NodeResponse",
    "VideoDeviceResponse",
    "ViewCreateRequest",
    "ViewResponse",
    "EnumTypeCreate",
    "EnumTypeUpdate",
    "EnumTypeResponse",
    "ResponseActionCreate",
    "ResponseActionUpdate",
    "ResponseActionResponse",
    "AlertGroupCreate",
    "AlertGroupUpdate",
    "AlertGroupResponse",
    "ResponseBindRequest",
    "ExceptionCreate",
    "ExceptionUpdate",
    "ExceptionResponse",
    "ExceptionListResponse",
    "EntityBindRequest",
    "ActionBindRequest",
    "SoundBindRequest",
    "EventResponse",
    "EventListResponse",
    "ExceptionStatsItem",
    "TrendItem",
]
