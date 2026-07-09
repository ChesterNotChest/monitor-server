## ADDED Requirements

### Requirement: 告警列表
系统 SHALL 提供 `GET /api/v1/alerts` 端点。支持分页 + 按严重级别/状态/时间范围筛选。三个角色均可访问。

### Requirement: 标记已处理
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/handle` 端点。将 SituationEvent 标记为已处理，写入 `handled_at` 和 `handled_by`（当前用户 ID）。安全员和负责人可访问。

### Requirement: 标记误报
系统 SHALL 提供 `PUT /api/v1/alerts/{id}/false-alarm` 端点。将 SituationEvent 标记为误报，写入 `handled_at` 和 `handled_by`。安全员和负责人可访问。
