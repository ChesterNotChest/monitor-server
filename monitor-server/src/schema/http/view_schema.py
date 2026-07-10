"""监控视图 HTTP 请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ViewCreateRequest(BaseModel):
    audio_id: int = Field(..., description="音频设备 ID")
    video_id: int = Field(..., description="视频设备 ID")


class ViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="监控视图 ID")
    audio_id: int = Field(..., description="关联音频设备 ID")
    video_id: int = Field(..., description="关联视频设备 ID")
    cache_path: str | None = Field(None, description="合流缓存文件路径")
    created_at: datetime | None = Field(None, description="视图创建时间")
    flv_url: str | None = Field(None, description="FLV 直播流地址（HTTP-FLV 播放）")
    webrtc_url: str | None = Field(None, description="WebRTC 直播流地址（低延迟播放）")
    rtmp_url: str | None = Field(None, description="RTMP 直播流地址（推流/拉流）")
    warnings: list[str] = Field(default_factory=list, description="视图创建/运行警告信息列表")


class ViewListResponse(BaseModel):
    """监控视图列表响应体。"""

    views: list[ViewResponse] = Field(..., description="监控视图列表")
