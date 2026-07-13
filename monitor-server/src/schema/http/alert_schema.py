"""告警处理 Schema。"""

from datetime import datetime
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: int = Field(..., description="告警 ID")
    view_id: int = Field(..., description="关联监控视图 ID")
    exception_id: int = Field(..., description="关联异常规则 ID")
    exception_name: str | None = Field(None, description="异常规则名称")
    severity: str | None = Field(None, description="严重级别")
    recording_id: int | None = Field(None, description="关联录像 ID（如有）")
    timestamp: datetime = Field(..., description="告警触发时间")
    status: str | None = Field(None, description="告警状态: created/acknowledged/escalated/handled/false_alarm")

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertResponse] = Field(..., description="告警列表")
    total: int = Field(..., description="告警总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
