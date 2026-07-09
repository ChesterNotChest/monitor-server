# RBAC 认证与权限系统设计

## Context

项目已有完整的 Repository 层（15 个 Repo）、部分 Service 层（node_task, view_task, node_stream_task）、部分 Network API（node_router, view_router, named_person）、Network WSS/RTMP 基础设施。NamedPerson 模块已完整实现（model/repo/schema/service/router），服务于人脸识别功能，不与用户管理关联。

当前缺失：User 模型、认证流程、RBAC 中间件，以及 Dashboard/Alert/Fence/Detection/Exception/Device/Log/Report/User 等业务 API。现有 `get_db()` 提供 Session 注入，Repository 均以构造函数 `__init__(self, db)` 接收 Session。

**重要区分**：用户管理模块管理的是使用系统的用户（安全员/负责人/运维员）；NamedPerson（命名人物）模块服务于人脸识别功能。两者互不关联。

## Goals / Non-Goals

**Goals:**
- User 模型 + JWT 认证（python-jose + passlib bcrypt）
- 三层 RBAC：security_guard（安全员）、manager（负责人）、operator（运维员）
- 每个用例对应的 Service + API endpoint，全部通过权限中间件保护
- Dashboard 聚合：态势统计实时查询 monitor_views + situation_events + nodes 表
- Alert 处理动作：mark_handled / mark_false_alarm（写入新表 `alert_reviews`，不改动 SituationEvent）
- 种子管理员：首次启动自动创建，密码写入文件

**Non-Goals:**
- 不实现 OAuth2 第三方登录
- 不实现 session 管理（JWT stateless）
- 不修改现有 model / repository / network 层（NamedPerson、SituationEvent 等均不动）
- 不实现前端路由或页面
- 不将 User 与 NamedPerson 关联

## Decisions

### 1. User Model

```python
# models/user.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[int]            # PK
    username: Mapped[str]      # unique, index
    password_hash: Mapped[str] # bcrypt hash
    role: Mapped[str]          # "security_guard" | "manager" | "operator"
    is_active: Mapped[bool]    # default True
    created_at: Mapped[datetime]
```

| 决策 | 选择 | 理由 |
|------|------|------|
| 密码方案 | bcrypt via passlib | OWASP 推荐，Python 生态标准 |
| Token | JWT HS256, 过期 8h | stateless，无需 Redis；8h 覆盖一个值班周期 |
| role 存储 | 单字段 String | 三种角色互斥，无需多对多关联 |
| 权限映射 | 代码级矩阵 dict | 不需要动态配置，简单直观 |
| .env 位置 | 项目最外层 `f:\小学期\monitor-server\.env` | 与现有 `config.py` 的 `env_file` 路径一致 |
| 种子管理员密码 | 写入 `admin_password.txt` 文件 | 首次启动后运维员可查看，生产部署前删除 |

### 2. 权限矩阵

```
PERMISSION                    SECURITY_GUARD   MANAGER   OPERATOR
────────────────────────────────────────────────────────────────
dashboard:view                    ✓              ✓          ✓
monitor:view                      ✓              ✓          ─
monitor:replay                    ✓              ✓          ─
alert:list                        ✓              ✓          ✓
alert:handle                      ✓              ✓          ─
fence:manage                      ✓              ─          ─
detection:manage                  ─              ✓          ─
exception:manage                  ─              ✓          ✓
alert_group:manage                ─              ✓          ✓
report:view                       ─              ✓          ─
device:onboard                    ─              ─          ✓
device:list                       ─              ─          ✓
device:health                     ─              ─          ✓
log:view                          ─              ─          ✓
user:manage                       ─              ─          ✓
```

注：`person:view` 不在 RBAC 矩阵中——NamedPerson API 已存在，其权限由 Part A 基础设施自行管理，本 change 不涉及。

### 3. RBAC 中间件设计

```python
# middleware/rbac.py
class Role(str, Enum):
    SECURITY_GUARD = "security_guard"
    MANAGER = "manager"
    OPERATOR = "operator"

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解码 JWT，从 DB 加载 User 实例。401 如果 token 无效。"""

def require_role(*roles: Role) -> Callable:
    """返回 Depends 可用的依赖。403 如果角色不匹配。"""

def require_permission(perm: str) -> Callable:
    """返回 Depends 可用的依赖。403 如果角色无此权限。"""
```

### 4. Alert 处理动作设计（不修改 SituationEvent）

SituationEvent 模型已由 yuyu 分支定义，当前分支与其一致，不做修改。告警处理记录写入独立新表 `alert_reviews`：

```python
# models/alert_review.py
class AlertReview(Base):
    __tablename__ = "alert_reviews"
    id: Mapped[int]             # PK
    alert_id: Mapped[int]       # FK → situation_events.id
    reviewer_id: Mapped[int]    # FK → users.id
    action: Mapped[str]         # "handled" | "false_alarm"
    reviewed_at: Mapped[datetime]
```

| action | 含义 | DB 变更 |
|--------|------|---------|
| `handled` | 标记为已处理 | INSERT alert_reviews (action=handled) |
| `false_alarm` | 标记为误报 | INSERT alert_reviews (action=false_alarm) |

### 5. API 端点设计

```
POST   /api/v1/auth/login        → {access_token, user}
POST   /api/v1/auth/logout       → {ok: true}  (client 侧删除 token)
GET    /api/v1/auth/me           → UserResponse

GET    /api/v1/dashboard/stats   → {total_views, active_alerts, online_nodes, ...}
GET    /api/v1/dashboard/trends  → {by_severity, by_time, ...}

GET    /api/v1/fences            → list[ElectronicFence]
POST   /api/v1/fences            → ElectronicFence
PUT    /api/v1/fences/{id}       → ElectronicFence
DELETE /api/v1/fences/{id}       → {ok: true}

GET    /api/v1/alerts            → list[SituationEvent]  (分页, filter by severity/time)
PUT    /api/v1/alerts/{id}/handle      → {ok: true}
PUT    /api/v1/alerts/{id}/false-alarm → {ok: true}

GET    /api/v1/detection/entity-types     → list[EntityType]
POST   /api/v1/detection/entity-types     → EntityType
PUT    /api/v1/detection/entity-types/{id} → EntityType
DELETE /api/v1/detection/entity-types/{id} → {ok: true}
# 同理 action-types, sound-types

GET    /api/v1/exceptions        → list[ExceptionDef]
POST   /api/v1/exceptions        → ExceptionDef
PUT    /api/v1/exceptions/{id}   → ExceptionDef
DELETE /api/v1/exceptions/{id}   → {ok: true}

GET    /api/v1/alert-groups      → list[AlertGroup]
POST   /api/v1/alert-groups      → AlertGroup
PUT    /api/v1/alert-groups/{id} → AlertGroup
DELETE /api/v1/alert-groups/{id} → {ok: true}

GET    /api/v1/devices/nodes     → list[Node]  (含 is_connected, last_seen)
GET    /api/v1/devices/nodes/{id}/health → {cpu, memory, disk, streaming_devices}
POST   /api/v1/devices/nodes/{id}/onboard → {ok: true}

GET    /api/v1/logs              → list[log entries] (分页, filter by level/时间)
GET    /api/v1/logs/{id}         → log detail

GET    /api/v1/reports/weekly    → {period, stats, top_alerts, ...}
GET    /api/v1/reports/monthly   → {period, stats, top_alerts, ...}

GET    /api/v1/users             → list[User]
POST   /api/v1/users             → User
PUT    /api/v1/users/{id}/role   → User
PUT    /api/v1/users/{id}/deactivate → {ok: true}
```

注：`/api/v1/persons` 已存在于 `network/api/named_person.py`，本 change 不重复创建。

### 6. 文件结构增量

```
.env                               ← MODIFY: 新增 JWT_SECRET
src/
├── models/
│   ├── user.py                    ← NEW
│   └── alert_review.py            ← NEW
├── repository/
│   ├── user_repo.py               ← NEW
│   └── alert_review_repo.py       ← NEW
├── schema/http/
│   ├── __init__.py                ← NEW: package (如不存在)
│   ├── auth_schema.py             ← NEW
│   ├── dashboard_schema.py        ← NEW
│   ├── alert_schema.py            ← NEW
│   ├── fence_schema.py            ← NEW
│   ├── detection_schema.py        ← NEW
│   ├── exception_schema.py        ← NEW
│   ├── alert_group_schema.py      ← NEW
│   ├── device_schema.py           ← NEW
│   ├── log_schema.py              ← NEW
│   ├── report_schema.py           ← NEW
│   └── common.py                  ← NEW: PaginatedResponse
├── service/
│   ├── auth_service.py            ← NEW
│   ├── dashboard_service.py       ← NEW
│   ├── alert_service.py           ← NEW
│   ├── fence_service.py           ← NEW
│   ├── detection_service.py       ← NEW
│   ├── exception_service.py       ← NEW
│   ├── alert_group_service.py     ← NEW
│   ├── device_service.py          ← NEW
│   ├── log_service.py             ← NEW
│   ├── report_service.py          ← NEW
│   ├── user_service.py            ← NEW
│   └── __init__.py                ← MODIFY
├── middleware/
│   ├── __init__.py                ← NEW
│   └── rbac.py                    ← NEW
└── network/api/
    ├── __init__.py                ← MODIFY
    ├── auth_router.py             ← NEW
    ├── dashboard_router.py        ← NEW
    ├── alert_router.py            ← NEW
    ├── fence_router.py            ← NEW
    ├── detection_router.py        ← NEW
    ├── exception_router.py        ← NEW
    ├── alert_group_router.py      ← NEW
    ├── device_router.py           ← NEW
    ├── log_router.py              ← NEW
    ├── report_router.py           ← NEW
    └── user_router.py             ← NEW
```

## Risks / Trade-offs

- **JWT 无状态**：无法主动失效 token → 8h 过期 + client 端删除即可满足需求
- **单 role 字段**：如果未来需要用户同时拥有多个角色 → 改为 `roles: JSON` 或关联表。当前阶段三种角色互斥，简单方案足够
- **Dashboard 实时性**：每次请求实时查询 DB → 数据量小时足够；未来可加 Redis 缓存
- **AlertReview 独立表**：与 SituationEvent 解耦，不影响 yuyu 分支模型；后续如需在 alert 列表中展示处理状态，JOIN alert_reviews 即可
