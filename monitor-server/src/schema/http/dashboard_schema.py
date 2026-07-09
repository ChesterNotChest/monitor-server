"""态势仪表板 Schema。"""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_views: int
    active_alerts: int
    online_nodes: int
    total_devices: int

    model_config = {"from_attributes": True}


class AlertTrendPoint(BaseModel):
    date: str
    severity: str
    count: int


class DashboardTrends(BaseModel):
    points: list[AlertTrendPoint]
