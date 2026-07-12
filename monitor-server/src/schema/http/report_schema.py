"""报表 Schema。"""

from pydantic import BaseModel, Field


class ReportItem(BaseModel):
    label: str = Field(..., description="统计项名称")
    value: int = Field(..., description="统计项数值")


class ReportResponse(BaseModel):
    period: str = Field(..., description="报表周期（如 2026-W01 / 2026-01）")
    total_alerts: int = Field(..., description="告警总数")
    by_severity: list[ReportItem] = Field(..., description="按严重级别分组的统计")
    top_exceptions: list[ReportItem] = Field(..., description="触发次数最多的异常类型排行")
