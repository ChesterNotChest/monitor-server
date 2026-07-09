# User Management API

**Purpose:** 系统用户管理（创建/角色修改/停用）——仅运维员可访问。与 NamedPerson 模块无关。

## Requirements

### Requirement: 用户管理
系统 SHALL 提供用户管理端点。仅运维员可访问。

- `GET /api/v1/users` — 用户列表
- `POST /api/v1/users` — 创建用户（含角色分配）
- `PUT /api/v1/users/{id}/role` — 修改用户角色
- `PUT /api/v1/users/{id}/deactivate` — 停用用户（软删除：is_active=false）

#### Scenario: 运维员创建安全员账户
- **WHEN** 运维员 POST /users {username: "guard01", password: "xxx", role: "security_guard"}
- **THEN** 密码以 bcrypt hash 存储，role 验证为有效值，创建成功
