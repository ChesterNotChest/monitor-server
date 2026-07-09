"""报表 Schema。"""

from pydantic import BaseModel


class ReportItem(BaseModel):
    label: str
    value: int


class ReportResponse(BaseModel):
    period: str
    total_alerts: int
    by_severity: list[ReportItem]
    top_exceptions: list[ReportItem]
