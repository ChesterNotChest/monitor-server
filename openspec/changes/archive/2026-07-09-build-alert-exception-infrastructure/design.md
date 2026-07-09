## Context

异常/告警体系的数据模型和 Repository 层已定义完毕：

| 层 | 已就绪 | 待建 |
|---|---|---|
| Model | EntityType, ActionType, SoundType, ResponseAction, AlertGroup, ExceptionDef (含 M2M 关联表), SituationEvent | — |
| Repo | 全部继承 BaseRepo + 专用查询方法（by_severity, by_group, by_view, by_time_range 等） | — |
| Service | — | alert_task + alert_module, exception_task + exception_module, event_task |
| Schema | — | enum_types, alert, exception, event（均放 `schema/http/`） |
| API | — | enum_types, alert, exception, event（均放 `network/api/`） |

遵循项目 Spec 规范：`service-layer`、`schema-convention`、`network-layer`。

## Goals / Non-Goals

**Goals:**
- 四张枚举表（EntityType / ActionType / SoundType / ResponseAction）的完整 CRUD Service + API
- AlertGroup CRUD + 独立 ResponseAction 枚举管理 + 嵌套绑定/解绑路由
- ExceptionDef CRUD + severity/group_id 管理 + 多对多绑定 EntityType/ActionType/SoundType
- SituationEvent 只读查询：按 view 过滤、按时间范围过滤、按 exception 分组 count 聚合、按时间段趋势统计
- 所有新增代码遵循 `*_task.py + *_module/` 结构

**Non-Goals:**
- 不实现 AI 检测引擎调度逻辑（那是后续模块的工作）
- 不实现告警推送/通知的实际发送（仅管理枚举和规则）
- 不实现告警超时自动升级/确认关闭状态机
- 不实现用户认证鉴权
- 不切换数据库引擎

## Decisions

### 1. 模块拆分：4 组 Service + API

**选择**: 按业务边界拆为 4 组，共享 `alert_module/` 和 `exception_module/` 内部逻辑包。

```
src/service/
├── enum_task.py                     ← 门户：EntityType/ActionType/SoundType CRUD
├── alert_task.py                    ← 门户：AlertGroup CRUD + ResponseAction CRUD + 绑定管理
│   └── alert_module/
│       ├── __init__.py
│       ├── group.py                 ← 内部：告警分组逻辑
│       └── response.py              ← 内部：响应动作 + 分组-响应关联
├── exception_task.py                ← 门户：ExceptionDef CRUD + AI类型绑定
│   └── exception_module/
│       ├── __init__.py
│       └── binding.py               ← 内部：管理 exception ↔ entity/action/sound M2M
└── event_task.py                    ← 门户：SituationEvent 查询 + 聚合统计
```

**理由**: EntityType/ActionType/SoundType 是简单枚举（仅 name 字段），合并为 `enum_task.py` 避免碎片化。ResponseAction 逻辑被合并到 `alert_task.py + alert_module/` 因其与 AlertGroup 紧密耦合。ExceptionDef 的 M2M 绑定逻辑复杂，独立为 `exception_module/binding.py`。

### 2. API 路由设计：独立 + 嵌套混合

**选择**: ResponseAction 枚举管理使用独立路由 `POST /api/v1/response-actions`，AlertGroup 与 ResponseAction 的绑定关系使用嵌套路由 `POST /api/v1/alert-groups/{id}/responses`。

完整路由规划：

| 路由文件 | 前缀 | 端点 |
|---------|------|------|
| `enum_types.py` | `/api/v1/entity-types` | CRUD |
| `enum_types.py` | `/api/v1/action-types` | CRUD |
| `enum_types.py` | `/api/v1/sound-types` | CRUD |
| `alert.py` | `/api/v1/response-actions` | CRUD（独立） |
| `alert.py` | `/api/v1/alert-groups` | CRUD |
| `alert.py` | `/api/v1/alert-groups/{id}/responses` | 绑定/解绑（嵌套） |
| `exception.py` | `/api/v1/exceptions` | CRUD |
| `exception.py` | `/api/v1/exceptions/{id}/entities` | 绑定/解绑 |
| `exception.py` | `/api/v1/exceptions/{id}/actions` | 绑定/解绑 |
| `exception.py` | `/api/v1/exceptions/{id}/sounds` | 绑定/解绑 |
| `event.py` | `/api/v1/events` | 查询 |
| `event.py` | `/api/v1/events/stats/by-exception` | 按 exception 分组 count |
| `event.py` | `/api/v1/events/stats/trend` | 按时间段趋势 |

**理由**: 独立路由管理枚举表自身的 CRUD（管理员增删可用的响应动作类型），嵌套路由管理"哪个告警分组触发哪些响应"的关联关系。两者职责清晰、互不干扰。

### 3. 聚合统计：Service 层直接 SQL

**选择**: `event_task.py` 中的聚合统计方法使用 SQLAlchemy `func.count()` + `group_by` + 时间粒度 `func.strftime()` 直接在数据库层完成聚合，不做 Python 侧后处理。

**理由**: SQLite 的 `strftime` 可以按小时/天/月聚合，数据量大时数据库聚合远快于 Python 循环。返回结构化的 `dict` 给 API 层序列化。

### 4. M2M 绑定管理：幂等设计

**选择**: 绑定操作（POST）幂等——已存在关联则静默成功；解绑操作（DELETE）幂等——不存在关联则静默成功。均返回当前完整关联列表。

**理由**: 前端可以用 PUT 语义做全量替换（先清空再逐个绑定），也可以用 POST/DELETE 做增量调整。幂等性降低客户端复杂度。

### 5. ResponseAction 归入 alert 模块

**选择**: `alert_task.py` 同时承担 AlertGroup 和 ResponseAction 的管理，`alert_module/response.py` 封装 ResponseAction 的 CRUD 和绑定逻辑。

**理由**: ResponseAction 的主要消费方是 AlertGroup（告警分组绑定响应动作）。将两者放在同一 task 下，`group.py` 可以直接 `from .response import ...` 调用，减少跨 task 依赖。

## Risks / Trade-offs

- **[R] ExceptionDef 绑定复杂度**: 创建异常规则时需要同时指定 severity + group_id + 可选绑定多种 AI 类型 → 分步操作：先创建 ExceptionDef，再逐个绑定 entities/actions/sounds。API 设计为两步（POST /exceptions 创建 → POST /exceptions/{id}/entities 绑定），避免单次请求过于复杂。
- **[R] 聚合查询性能**: 事件表数据量增长后聚合可能变慢 → 事件表已有 `view_id`、`exception_id`、`timestamp` 索引。后续可加 `timestamp` 复合索引优化时间范围聚合。
- **[R] alert_task.py 职责略重**: 同时管理 AlertGroup 和 ResponseAction → 如果后续 ResponseAction 逻辑复杂度增加，可拆分为独立 `response_action_task.py`。当前规模下合并是合理的。

## Migration Plan

1. 创建 `enum_task.py` + `alert_task.py` + `alert_module/` + `exception_task.py` + `exception_module/` + `event_task.py`
2. 创建 `schema/http/enum_types.py`、`alert.py`、`exception.py`、`event.py`
3. 创建 `network/api/enum_types.py`、`alert.py`、`exception.py`、`event.py`
4. 更新 `network/api/__init__.py` 注册新路由（追加到 routers 列表）
5. 无需迁移已有代码 —— 纯增量，不涉及模型/仓库/配置变更
