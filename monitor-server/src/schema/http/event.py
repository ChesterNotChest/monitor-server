"""事件日志与统计 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class EventResponse(BaseModel):
    """事件响应体。"""

    id: int
    view_id: int
    exception_id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """事件分页列表响应体。"""

    items: list[EventResponse]
    total: int
    page: int
    page_size: int


class ExceptionStatsItem(BaseModel):
    """按异常分组统计项。"""

    exception_id: int
    exception_severity: str
    count: int


class TrendItem(BaseModel):
    """时间段趋势统计项。"""

    period: str
    count: int
