"""录制回放 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class RecordingResponse(BaseModel):
    """录制记录响应体。"""

    id: int = Field(..., description="录制记录 ID")
    view_id: int = Field(..., description="关联监控视图 ID")
    file_path: str = Field(..., description="录制文件路径")
    start_time: datetime = Field(..., description="录制开始时间")
    end_time: datetime | None = Field(None, description="录制结束时间（录制中则为空）")

    model_config = {"from_attributes": True}
