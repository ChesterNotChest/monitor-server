## ADDED Requirements

### Requirement: JWT 认证依赖
系统 SHALL 提供 FastAPI `Depends(get_current_user)` 依赖注入。从请求头 Authorization Bearer token 中解码 JWT，验证签名和过期时间，加载 User 实例。无效 token 返回 401。

### Requirement: 角色检查依赖
系统 SHALL 提供 `Depends(require_role(*roles))` 依赖注入。在 get_current_user 之后检查当前用户角色是否在允许的角色列表中。不匹配返回 403。

### Requirement: 权限检查依赖
系统 SHALL 提供 `Depends(require_permission(perm))` 依赖注入。通过权限矩阵 `PERMISSIONS` 检查当前用户角色是否拥有指定权限。不匹配返回 403。

#### Scenario: 安全员访问电子围栏
- **WHEN** 安全员调用 `POST /api/v1/fences`，端点包含 `Depends(require_permission("fence:manage"))`
- **THEN** 权限检查通过，请求正常处理

#### Scenario: 运维员访问电子围栏被拒
- **WHEN** 运维员调用 `POST /api/v1/fences`
- **THEN** 返回 403，因为 operator 无 fence:manage 权限
