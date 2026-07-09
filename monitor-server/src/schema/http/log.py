"""日志 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class LogEntryResponse(BaseModel):
    """日志条目响应体。"""

    id: int
    log_type: int
    operator_id: int | None = None
    view_id: int | None = None
    event_id: int | None = None
    severity: int | None = None
    summary: str
    details_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    """日志分页列表响应体。"""

    items: list[LogEntryResponse]
    total: int
    page: int
    page_size: int


class LogStatsItem(BaseModel):
    """日志统计项。"""

    value: int
    count: int
