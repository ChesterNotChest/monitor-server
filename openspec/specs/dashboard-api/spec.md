# Dashboard API

**Purpose:** 态势仪表板数据聚合——所有角色可访问。

## Requirements

### Requirement: 态势统计
系统 SHALL 提供 `GET /api/v1/dashboard/stats` 端点。实时聚合返回：活跃 View 数、未处理告警数、在线 Node 数、设备总数。三个角色均可访问。

### Requirement: 告警趋势
系统 SHALL 提供 `GET /api/v1/dashboard/trends` 端点。返回最近 7 天按严重级别分组的告警趋势数据，以及按时间分布的数量变化。
