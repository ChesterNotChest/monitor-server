## ADDED Requirements

### Requirement: 告警分级 CRUD
系统 SHALL 提供 `AlertGroup` 的 CRUD 端点。负责人和运维员可访问。

- `GET /api/v1/alert-groups` — 列表（含关联的 ResponseAction）
- `POST /api/v1/alert-groups` — 创建告警分组
- `PUT /api/v1/alert-groups/{id}` — 更新告警分组
- `DELETE /api/v1/alert-groups/{id}` — 删除告警分组
