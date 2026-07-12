## MODIFIED Requirements

### Requirement: 异常定义 CRUD
系统 SHALL 提供 `ExceptionDef` 的 CRUD 端点。负责人和运维员可访问。

- `GET /api/v1/exceptions` — 列表
- `POST /api/v1/exceptions` — 创建异常定义
- `PUT /api/v1/exceptions/{id}` — 更新异常定义
- `DELETE /api/v1/exceptions/{id}` — 删除异常定义
