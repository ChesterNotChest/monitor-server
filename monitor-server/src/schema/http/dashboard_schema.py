"""态势仪表板 Schema。"""

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    total_views: int = Field(..., description="监控视图总数")
    active_alerts: int = Field(..., description="活跃告警数")
    online_nodes: int = Field(..., description="在线计算节点数")
    total_devices: int = Field(..., description="设备总数（视频 + 音频）")

    model_config = {"from_attributes": True}


class AlertTrendPoint(BaseModel):
    date: str = Field(..., description="日期（ISO 8601 格式）")
    severity: str = Field(..., description="告警严重级别")
    count: int = Field(..., description="该日期的告警数量")


class DashboardTrends(BaseModel):
    points: list[AlertTrendPoint] = Field(default_factory=list, description="告警趋势数据点列表")
