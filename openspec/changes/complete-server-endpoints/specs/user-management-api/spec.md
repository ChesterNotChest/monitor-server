# User Management API (Delta)

## ADDED Requirements

### Requirement: Dual UserResponse distinction is documented

系统存在两个 UserResponse 模型——`auth_schema.py::UserResponse`（用于登录和 /auth/me）和 `user.py::UserResponse`（用于 /users CRUD）。两个模型的字段差异 SHALL 在 Swagger 中清晰可见：
- auth 版本：`{ id, username, role (str), is_active }`
- user 版本：`{ id, username, role (int), created_at }`

前端开发者 SHALL 能在 Swagger 中区分两个 UserResponse 的不同结构。

#### Scenario: Auth me endpoint shows auth-style UserResponse

- **WHEN** 前端开发者打开 `GET /api/v1/auth/me`
- **THEN** Swagger 展示的 UserResponse 包含 `role: string` 和 `is_active: boolean`

#### Scenario: User list endpoint shows user-style UserResponse

- **WHEN** 前端开发者打开 `GET /api/v1/users`
- **THEN** Swagger 展示的 UserResponse 包含 `role: integer` 和 `created_at: string`
- **AND** Swagger 中该模型的 role 字段 description 说明 "1=安全员 2=管理员 3=负责人 4=运维员"

### Requirement: User management endpoints declare error responses

用户管理端点 SHALL 在 Swagger 中声明可能的错误响应。

#### Scenario: Create user declares conflict error

- **WHEN** 前端开发者打开 `POST /api/v1/users`
- **THEN** Swagger Responses 区域展示 `409: 用户名已存在`
- **AND** 描述区域展示 "**权限**: user:manage"

#### Scenario: Deactivate user declares not found error

- **WHEN** 前端开发者打开 `PUT /api/v1/users/{user_id}/deactivate`
- **THEN** Swagger Responses 区域展示 `404: 用户不存在`
