## ADDED Requirements

### Requirement: 用户登录
系统 SHALL 提供 `POST /api/v1/auth/login` 端点。接收 `{username, password}`，验证密码后返回 JWT access_token 和用户信息。token 有效期 8 小时，使用 HS256 签名。

#### Scenario: 登录成功
- **WHEN** 提供正确的 username 和 password
- **THEN** 返回 `{access_token: "<jwt>", token_type: "bearer", user: {id, username, role}}`

#### Scenario: 密码错误
- **WHEN** 提供错误的 password
- **THEN** 返回 401

### Requirement: 获取当前用户
系统 SHALL 提供 `GET /api/v1/auth/me` 端点。从 Authorization header 解析 JWT，返回当前用户信息。

#### Scenario: 有效 token
- **WHEN** 携带有效 Authorization: Bearer <token>
- **THEN** 返回当前用户的 id、username、role
