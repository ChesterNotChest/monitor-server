"""设备管理 Schema。"""

from datetime import datetime
from pydantic import BaseModel


class NodeDeviceResponse(BaseModel):
    id: int
    name: str
    streaming: bool | None = None

    model_config = {"from_attributes": True}


class NodeHealthResponse(BaseModel):
    node_id: int
    is_connected: bool
    video_devices: int
    audio_devices: int
    streaming_devices: int

    model_config = {"from_attributes": True}
