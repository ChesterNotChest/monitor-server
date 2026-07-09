# Tasks — 多角色 RBAC 认证系统

> 按 Phase 1→2→3 顺序实施。Phase 1 是所有后续 Phase 的前置条件。
> **SituationEvent 不修改**（yuyu 分支对齐）。**NamedPerson 不动**（已实现，人脸识别专用，与用户管理无关）。

## Phase 1 — 认证地基

### 1.1 依赖与配置
- [x] 1.1.1 在 `requirements.txt` 中新增 `python-jose[cryptography]` 和 `bcrypt`
- [x] 1.1.2 在 `config.py` 中新增 `JWT_SECRET`、`JWT_ALGORITHM=HS256`、`JWT_EXPIRE_HOURS=8` 配置项
- [x] 1.1.3 在项目 `.env` 中添加 `JWT_SECRET` 默认值

### 1.2 User 模型
- [x] 1.2.1 创建 `src/models/user.py` — `User` 模型（id/username/password_hash/role/is_active/created_at）
- [x] 1.2.2 更新 `src/models/__init__.py` 导入 User

### 1.3 认证 Service
- [x] 1.3.1 确保 `src/schema/http/__init__.py` 包存在
- [x] 1.3.2 创建 `src/schema/http/auth_schema.py` — `LoginRequest`、`LoginResponse`、`UserResponse`
- [x] 1.3.3 创建 `src/repository/user_repo.py` — `UserRepo(BaseRepo[User])`，新增 `by_username(username)`
- [x] 1.3.4 更新 `src/repository/__init__.py` 导出 UserRepo
- [x] 1.3.5 创建 `src/service/auth_service.py` — `hash_password()`、`verify_password()`、`create_token()`、`verify_token()`、`login()`、`get_me()`

### 1.4 RBAC 中间件
- [x] 1.4.1 在 `src/constants.py` 中新增 `class Role(str, Enum)`（SECURITY_GUARD / MANAGER / OPERATOR）
- [x] 1.4.2 创建 `src/middleware/__init__.py`
- [x] 1.4.3 创建 `src/middleware/rbac.py` — `get_current_user()`、`require_role(*roles)`、`require_permission(perm)`、`PERMISSIONS` 矩阵

### 1.5 Auth API
- [x] 1.5.1 创建 `src/network/api/auth_router.py` — `POST /auth/login`、`POST /auth/logout`、`GET /auth/me`
- [x] 1.5.2 更新 `src/network/api/__init__.py` 注册 auth_router
- [x] 1.5.3 更新 `src/app.py` 加载 auth_router

### 1.6 管理员种子
- [x] 1.6.1 创建 `src/seed.py` — 首次启动自动创建 admin，密码写入 `admin_password.txt`
- [x] 1.6.2 更新 `src/app.py` — startup 事件中调用 seed 逻辑

## Phase 2 — 共享用例 API

### 2.1 Dashboard
- [x] 2.1.1 创建 `src/schema/http/dashboard_schema.py`
- [x] 2.1.2 创建 `src/service/dashboard_service.py` — `get_stats(db)`、`get_trends(db)`
- [x] 2.1.3 创建 `src/network/api/dashboard_router.py`
- [x] 2.1.4 更新 `src/network/api/__init__.py`

### 2.2 Alert
- [x] 2.2.1 创建 `src/models/alert_review.py` — `AlertReview` 模型（alert_id/reviewer_id/action/reviewed_at）
- [x] 2.2.2 更新 `src/models/__init__.py` 导入 AlertReview
- [x] 2.2.3 创建 `src/repository/alert_review_repo.py` — `AlertReviewRepo(BaseRepo[AlertReview])`
- [x] 2.2.4 创建 `src/schema/http/alert_schema.py`
- [x] 2.2.5 创建 `src/service/alert_service.py` — `list_alerts(db, filters)`、`mark_handled(db, alert_id, user_id)`、`mark_false_alarm(db, alert_id, user_id)`
- [x] 2.2.6 创建 `src/network/api/alert_router.py`
- [x] 2.2.7 更新 `src/network/api/__init__.py`

### 2.3 Device
- [x] 2.3.1 创建 `src/schema/http/device_schema.py`
- [x] 2.3.2 创建 `src/service/device_service.py` — `list_nodes(db)`、`get_node_health(db, node_id)`、`onboard_device(db, node_id)`
- [x] 2.3.3 创建 `src/network/api/device_router.py`
- [x] 2.3.4 更新 `src/network/api/__init__.py`

## Phase 3 — 差异化用例 API

### 3.1 安全员独有 — Fence
- [x] 3.1.1 创建 `src/schema/http/fence_schema.py`
- [x] 3.1.2 创建 `src/service/fence_service.py`
- [x] 3.1.3 创建 `src/network/api/fence_router.py`（require_permission("fence:manage")）
- [x] 3.1.4 更新 `src/network/api/__init__.py`

### 3.2 负责人独有 — Detection Enum
- [x] 3.2.1 创建 `src/schema/http/detection_schema.py`
- [x] 3.2.2 创建 `src/service/detection_service.py`
- [x] 3.2.3 创建 `src/network/api/detection_router.py`（require_permission("detection:manage")）
- [x] 3.2.4 更新 `src/network/api/__init__.py`

### 3.3 负责人+运维员 — Exception
- [x] 3.3.1 创建 `src/schema/http/exception_schema.py`
- [x] 3.3.2 创建 `src/service/exception_service.py`
- [x] 3.3.3 创建 `src/network/api/exception_router.py`
- [x] 3.3.4 更新 `src/network/api/__init__.py`

### 3.4 负责人+运维员 — Alert Group
- [x] 3.4.1 创建 `src/schema/http/alert_group_schema.py`
- [x] 3.4.2 创建 `src/service/alert_group_service.py`
- [x] 3.4.3 创建 `src/network/api/alert_group_router.py`
- [x] 3.4.4 更新 `src/network/api/__init__.py`

### 3.5 负责人独有 — Report
- [x] 3.5.1 创建 `src/schema/http/report_schema.py`
- [x] 3.5.2 创建 `src/service/report_service.py` — `get_weekly_report(db)`、`get_monthly_report(db)`
- [x] 3.5.3 创建 `src/network/api/report_router.py`（require_permission("report:view")）
- [x] 3.5.4 更新 `src/network/api/__init__.py`

### 3.6 运维员独有 — Log
- [x] 3.6.1 创建 `src/schema/http/log_schema.py`
- [x] 3.6.2 创建 `src/service/log_service.py`
- [x] 3.6.3 创建 `src/network/api/log_router.py`（require_permission("log:view")）
- [x] 3.6.4 更新 `src/network/api/__init__.py`

### 3.7 运维员独有 — User Management
- [x] 3.7.1 创建 `src/service/user_service.py` — `list_users()`、`create_user()`、`update_role()`、`deactivate_user()`
- [x] 3.7.2 创建 `src/network/api/user_router.py`（require_permission("user:manage")）
- [x] 3.7.3 更新 `src/network/api/__init__.py`

## Phase 4 — 收尾

### 4.1 Service 包初始化
- [x] 4.1.1 更新 `src/service/__init__.py` — 导入所有新 service 模块

### 4.2 测试
- [x] 4.2.1 创建 `src/tests/test_auth.py` — 登录/Token/角色校验测试
- [x] 4.2.2 创建 `src/tests/test_rbac.py` — 权限矩阵测试（三个角色分别测越权拒绝）
- [x] 4.2.3 创建 `src/tests/test_alert_service.py` — 告警处理测试
- [x] 4.2.4 conftest.py 已提供 db/engine fixture，test_auth.py 自带 client fixture
- [x] 4.3.1 README.md 已添加认证说明（默认管理员、角色权限表）
