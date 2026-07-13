## MODIFIED Requirements

### Requirement: 告警列表

系统 SHALL 提供 `GET /api/v1/alerts` 端点。支持分页 + 按严重级别/状态/时间范围筛选。三个角色均可访问。告警引擎创建新的告警事件时，系统 SHALL 同步创建一条结构化 `LogEntry`，供 `GET /api/v1/logs` 展示。

#### Scenario: 告警事件可在日志中心追踪

- **WHEN** 告警引擎创建新的 `SituationEvent`
- **THEN** `GET /api/v1/alerts` 可查询该告警事件
- **AND** `GET /api/v1/logs` 可查询到关联 `event_id` 的告警触发日志
