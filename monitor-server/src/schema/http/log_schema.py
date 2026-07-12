"""系统日志 Schema。"""

from datetime import datetime
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    id: int = Field(..., description="日志 ID")
    level: str = Field(..., description="日志级别（INFO / WARNING / ERROR）")
    message: str = Field(..., description="日志内容")
    timestamp: datetime = Field(..., description="日志时间")

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogEntry] = Field(..., description="日志列表")
    total: int = Field(..., description="日志总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
