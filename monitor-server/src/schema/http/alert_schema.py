"""告警处理 Schema。"""

from datetime import datetime
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    view_id: int
    exception_id: int
    recording_id: int | None = None
    timestamp: datetime
    # 处理状态通过 JOIN alert_reviews 获得（后续扩展）

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
