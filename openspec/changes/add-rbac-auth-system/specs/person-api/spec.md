## ADDED Requirements

### Requirement: 命名人物 CRUD
系统 SHALL 提供命名人物的完整 CRUD 端点。仅负责人可访问。

- `GET /api/v1/persons` — 列出所有命名人物
- `POST /api/v1/persons` — 注册新人物（含面部特征向量）
- `PUT /api/v1/persons/{id}` — 更新人物信息
- `DELETE /api/v1/persons/{id}` — 删除人物
