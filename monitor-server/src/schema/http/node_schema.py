"""Node 与设备相关 HTTP 响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="视频设备 ID")
    name: str = Field(..., description="视频设备名称")
    node_id: int = Field(..., description="所属计算节点 ID")
    streaming: bool = Field(..., description="是否正在推流")


class AudioDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="音频设备 ID")
    name: str = Field(..., description="音频设备名称")
    node_id: int = Field(..., description="所属计算节点 ID")
    streaming: bool = Field(..., description="是否正在推流")


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="计算节点 ID")
    is_connected: bool = Field(..., description="节点是否在线")
    last_seen: datetime | None = Field(None, description="最后在线时间")


class NodeListResponse(BaseModel):
    """计算节点列表响应体。"""

    nodes: list[NodeResponse] = Field(..., description="计算节点列表")


class VideoDeviceListResponse(BaseModel):
    """视频设备列表响应体。"""

    videos: list[VideoDeviceResponse] = Field(..., description="视频设备列表")


class AudioDeviceListResponse(BaseModel):
    """音频设备列表响应体。"""

    audios: list[AudioDeviceResponse] = Field(..., description="音频设备列表")
