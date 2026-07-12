"""事件日志与统计 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    """事件响应体。"""

    id: int = Field(..., description="事件 ID")
    view_id: int = Field(..., description="关联监控视图 ID")
    exception_id: int = Field(..., description="关联异常规则 ID")
    recording_id: int | None = Field(None, description="关联录制 ID（如有）")
    timestamp: datetime = Field(..., description="事件触发时间")

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """事件分页列表响应体。"""

    items: list[EventResponse] = Field(..., description="事件列表")
    total: int = Field(..., description="事件总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")


class ExceptionStatsItem(BaseModel):
    """按异常分组统计项。"""

    exception_id: int = Field(..., description="异常规则 ID")
    exception_severity: str = Field(..., description="异常严重级别")
    count: int = Field(..., description="该异常类型的事件数量")


class TrendItem(BaseModel):
    """时间段趋势统计项。"""

    period: str = Field(..., description="时间段标识（如 2026-01-01）")
    count: int = Field(..., description="该时间段的事件数量")
