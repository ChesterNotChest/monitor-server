# RBAC Middleware

**Purpose:** FastAPI 依赖注入形式的认证与权限中间件。三角色（安全员/负责人/运维员）+ 权限矩阵。

## Requirements

### Requirement: JWT 认证依赖
系统 SHALL 提供 FastAPI `Depends(get_current_user)` 依赖注入。从请求头 Authorization Bearer token 中解码 JWT，验证签名和过期时间，加载 User 实例。无效 token 返回 401。

### Requirement: 角色检查依赖
系统 SHALL 提供 `Depends(require_role(*roles))` 依赖注入。在 get_current_user 之后检查当前用户角色是否在允许的角色列表中。不匹配返回 403。

### Requirement: 权限检查依赖
系统 SHALL 提供 `Depends(require_permission(perm))` 依赖注入。通过权限矩阵 `PERMISSIONS` 检查当前用户角色是否拥有指定权限。不匹配返回 403。

OPERATOR 角色 SHALL 拥有所有权限（dashboard:view, monitor:view, monitor:replay, alert:list, alert:handle, fence:manage, detection:manage, exception:manage, alert_group:manage, report:view, device:onboard, device:list, device:health, log:view, user:manage），作为技术管理员角色。

#### Scenario: 安全员访问电子围栏
- **WHEN** 安全员调用 `POST /api/v1/fences`，端点包含 `Depends(require_permission("fence:manage"))`
- **THEN** 权限检查通过，请求正常处理

#### Scenario: 运维员访问电子围栏通过
- **WHEN** 运维员调用 `POST /api/v1/fences`
- **THEN** 权限检查通过，因为 OPERATOR 拥有 fence:manage 权限

#### Scenario: 安全员访问用户管理被拒
- **WHEN** 安全员调用 `GET /api/v1/users`
- **THEN** 返回 403，因为 security_guard 无 user:manage 权限
