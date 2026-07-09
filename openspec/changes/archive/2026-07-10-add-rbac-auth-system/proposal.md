## Why

当前系统缺少用户认证与权限控制。前端需要三种角色（安全员、负责人、运维员）的操作入口，但后端没有任何用户模型、登录机制、或 RBAC 中间件。Dashboard、告警处理、电子围栏管理、枚举管理、设备管理等用例的 API 处于空白状态。需要补齐认证地基 + 角色用例的完整 API 面。

## What Changes

### Phase 1 — 认证地基（必须先做）
- 新增 `User` 模型（username、password_hash、role、is_active）
- 新增 JWT 认证服务（`python-jose` + `passlib[bcrypt]`）
- 新增 RBAC 中间件 `Depends(require_role(...))` 和 `Depends(require_permission(...))`
- 新增 `POST /auth/login`、`POST /auth/logout`、`GET /auth/me`

### Phase 2 — 共享用例 API（三个角色共用）
- 新增 Dashboard 聚合 API：态势统计、告警趋势
- 新增 Alert API CRUD + 处理动作（标记已处理/标记为误报）
- 新增 Device API：设备列表、健康状态、设备接入

### Phase 3 — 差异化用例 API（按角色）
- 安全员独有：Fence CRUD（电子围栏绘制+关联监控）
- 负责人独有：Person CRUD、Detection 枚举管理、Exception/AlertGroup CRUD、Report 周报月报
- 运维员独有：Log 查看、User CRUD + 角色管理

## Capabilities

### New Capabilities
- `user-model`: User 数据模型（id/username/password_hash/role/is_active）
- `auth-service`: JWT 签发/验证，登录/注销/当前用户查询
- `rbac-middleware`: FastAPI Depends 依赖注入，require_role / require_permission
- `dashboard-api`: 态势仪表板数据聚合服务
- `alert-api`: 告警列表查询 + 处理（标记已处理/误报）
- `fence-api`: 电子围栏 CRUD（安全员专有）
- `person-api`: 命名人物 CRUD（负责人专有）
- `detection-enum-api`: 实体/行为/声音枚举管理（负责人专有）
- `exception-api`: 异常定义 CRUD（负责人+运维员）
- `alert-group-api`: 告警分级 CRUD（负责人+运维员）
- `device-api`: 设备接入/列表/健康（运维员专有）
- `log-api`: 系统日志查看（运维员专有）
- `report-api`: 周报/月报（负责人专有）
- `user-management-api`: 用户管理 + 角色分配（运维员专有）

### Modified Capabilities
_无_（纯新增功能，不修改现有 spec）

## Impact

- 新增文件：`models/user.py`、`repository/user_repo.py`、`service/auth_service.py`、`middleware/rbac.py`、`schema/http/` 下 8+ 个 schema 文件、`network/api/` 下 12+ 个路由文件、`service/` 下 10+ 个服务模块
- 新增依赖：`python-jose[cryptography]`、`passlib[bcrypt]`、`httpx`（测试用）
- 修改文件：`app.py`（注册新路由 + 认证中间件）、`constants.py`（新增 Role 枚举）、`repository/__init__.py`（导出 UserRepo）
- 数据库变更：新增 `users` 表（`Base.metadata.create_all` 自动覆盖）
