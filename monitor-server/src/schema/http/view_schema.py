"""监控视图 HTTP 请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ViewCreateRequest(BaseModel):
    audio_id: int
    video_id: int


class ViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    audio_id: int
    video_id: int
    cache_path: str | None = None
    created_at: datetime | None = None
    flv_url: str | None = None
    webrtc_url: str | None = None
    rtmp_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
