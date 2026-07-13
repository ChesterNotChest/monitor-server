"""设备管理 Schema。"""

from datetime import datetime
from pydantic import BaseModel, Field


class NodeDeviceResponse(BaseModel):
    id: int = Field(..., description="设备 ID")
    name: str = Field(..., description="设备名称")
    streaming: bool | None = Field(None, description="是否正在推流")

    model_config = {"from_attributes": True}


class NodeHealthResponse(BaseModel):
    node_id: int = Field(..., description="计算节点 ID")
    is_connected: bool = Field(..., description="节点是否在线")
    video_devices: int = Field(..., description="视频设备数量")
    audio_devices: int = Field(..., description="音频设备数量")
    streaming_devices: int = Field(..., description="正在推流的设备数量")

    model_config = {"from_attributes": True}


class DeviceCreateRequest(BaseModel):
    """向虚拟 Node 注册自定义流设备请求体。"""

    device_type: str = Field(..., description="设备类型: video 或 audio")
    name: str = Field(..., description="设备名称")
    stream_url: str = Field(..., description="RTMP 流地址")


class DeviceCreateResponse(BaseModel):
    """自定义流设备创建响应体。"""

    id: int = Field(..., description="设备 ID")
    name: str = Field(..., description="设备名称")
    device_type: str = Field(..., description="设备类型: video 或 audio")
    node_id: int = Field(..., description="所属 Node ID")
    stream_url: str | None = Field(None, description="RTMP 流地址")

    model_config = {"from_attributes": True}
