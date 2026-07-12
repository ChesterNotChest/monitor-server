"""日志 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class LogEntryResponse(BaseModel):
    """日志条目响应体。"""

    id: int = Field(..., description="日志 ID")
    log_type: int = Field(..., description="日志类型编号")
    operator_id: int | None = Field(None, description="操作人用户 ID")
    view_id: int | None = Field(None, description="关联监控视图 ID")
    event_id: int | None = Field(None, description="关联事件 ID")
    severity: int | None = Field(None, description="严重级别")
    summary: str = Field(..., description="日志摘要")
    details_json: str | None = Field(None, description="详细信息（JSON 字符串）")
    created_at: datetime = Field(..., description="日志创建时间")

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    """日志分页列表响应体。"""

    items: list[LogEntryResponse] = Field(..., description="日志列表")
    total: int = Field(..., description="日志总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")


class LogStatsItem(BaseModel):
    """日志统计项。"""

    value: int = Field(..., description="统计维度值")
    count: int = Field(..., description="该维度的数量")
