# RBAC Middleware (Delta)

## ADDED Requirements

### Requirement: Permission strings are visible in Swagger

所有使用 `Depends(require_permission(...))` 的端点 SHALL 在函数 docstring 中标注所需权限标识符，格式为 `**权限**: <permission_string>`。Swagger 会自动将 docstring 渲染为端点描述，使前端开发者无需阅读后端源码即可了解权限要求。

#### Scenario: Alert handle endpoint shows permission

- **WHEN** 前端开发者打开 `PUT /api/v1/alerts/{alert_id}/handle` 的 Swagger 文档
- **THEN** 描述区域显示 "**权限**: alert:handle"

#### Scenario: User management endpoint shows permission

- **WHEN** 前端开发者打开 `GET /api/v1/users` 的 Swagger 文档
- **THEN** 描述区域显示 "**权限**: user:manage"

#### Scenario: Unprotected endpoint has no permission label

- **WHEN** 前端开发者打开 `POST /api/v1/auth/login`
- **THEN** 描述区域不包含 "**权限**:" 标注
