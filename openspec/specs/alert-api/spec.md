# Alert API

**Purpose:** 告警列表查询与处理（标记已处理/误报）。告警审查记录写入独立 `alert_reviews` 表，不修改 SituationEvent。

## Requirements

### Requirement: 告警列表
系统 SHALL 提供 `GET /api/v1/alerts` 端点。支持分页 + 按严重级别/状态/时间范围筛选。三个角色均可访问。

### Requirement: 标记已处理
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/handle` 端点。写入 `alert_reviews` 表（action=handled），记录处理人和时间。安全员和负责人可访问。

### Requirement: 标记误报
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/false-alarm` 端点。写入 `alert_reviews` 表（action=false_alarm）。安全员和负责人可访问。
