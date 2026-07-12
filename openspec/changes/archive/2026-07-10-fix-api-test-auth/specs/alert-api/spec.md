## MODIFIED Requirements

### Requirement: 标记已处理
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/handle` 端点。写入 `alert_reviews` 表（action=handled），记录处理人和时间。安全员、负责人和运维员可访问。

#### Scenario: 运维员标记告警已处理
- **WHEN** 运维员调用 `PUT /api/v1/alerts/1/handle`
- **THEN** 权限检查通过（若告警存在则正常处理，不存在则返回 404）

### Requirement: 标记误报
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/false-alarm` 端点。写入 `alert_reviews` 表（action=false_alarm）。安全员、负责人和运维员可访问。

#### Scenario: 运维员标记告警误报
- **WHEN** 运维员调用 `PUT /api/v1/alerts/1/false-alarm`
- **THEN** 权限检查通过（若告警存在则正常标记，不存在则返回 404）
