"""Node WebSocket 连接握手与流控制命令模型。"""

from typing import Literal

from pydantic import BaseModel


class DeviceInfo(BaseModel):
    id: int
    name: str


class ConnectRequest(BaseModel):
    token: str


class ConnectResponse(BaseModel):
    session_token: str
    videos: list[DeviceInfo]
    audios: list[DeviceInfo]


class UpdateStreamRequest(BaseModel):
    command: Literal["UPDATE_STREAM"] = "UPDATE_STREAM"
    device_type: Literal["audio", "video"]
    device_id: int
    enable: bool


class UpdateStreamResponse(BaseModel):
    success: bool
    message: str | None = None
