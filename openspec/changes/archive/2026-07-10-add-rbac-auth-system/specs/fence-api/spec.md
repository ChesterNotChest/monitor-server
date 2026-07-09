## ADDED Requirements

### Requirement: 电子围栏 CRUD
系统 SHALL 提供电子围栏的完整 CRUD 端点。仅安全员可访问。

- `GET /api/v1/fences` — 列出所有电子围栏
- `POST /api/v1/fences` — 创建电子围栏（含坐标 JSON）
- `PUT /api/v1/fences/{id}` — 更新围栏坐标
- `DELETE /api/v1/fences/{id}` — 删除围栏
