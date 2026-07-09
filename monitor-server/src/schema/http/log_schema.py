"""系统日志 Schema。"""

from datetime import datetime
from pydantic import BaseModel


class LogEntry(BaseModel):
    id: int
    level: str
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogEntry]
    total: int
    page: int
    page_size: int
