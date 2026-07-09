"""Node 与设备相关 HTTP 响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    node_id: int
    streaming: bool


class AudioDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    node_id: int
    streaming: bool


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_connected: bool
    last_seen: datetime | None = None
