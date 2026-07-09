## Why

异常/告警体系的数据模型和 Repository 层已通过前期 Spec 构建完成，但 Service 层和 API 层完全空白。智能识别检测模块（YOLO 目标、SlowFast 行为、YAMNet 声音）和告警管理处置模块（分级、通知、升级、确认/关闭）都依赖这些基础设施。现在需要补齐 Service + Schema + API 三层，为后续 AI 检测引擎和告警调度引擎提供可调用的 CRUD 和查询入口。

## What Changes

- 枚举表管理：EntityType、ActionType、SoundType、ResponseAction 四张枚举表的 CRUD Service + API
- AlertGroup 告警分组管理：CRUD + 绑定/解绑 ResponseAction（独立路由 + 嵌套路由）
- ExceptionDef 异常规则管理：CRUD + 绑定/解绑 AI 检测类型（EntityType/ActionType/SoundType）
- SituationEvent 事件日志查询：只读查询 + 按 view 过滤 + 按时间范围过滤 + 聚合统计（按 exception 分组 count、按时间段趋势）
- Schema 层：新增 `schema/http/alert.py`、`schema/http/exception.py`、`schema/http/event.py`、`schema/http/enum_types.py`
- API 层：新增 `src/network/api/alert.py`、`src/network/api/exception.py`、`src/network/api/event.py`、`src/network/api/enum_types.py`
- Service 层：新增 `alert_task.py + alert_module/`、`exception_task.py + exception_module/`、`event_task.py`
- 命名遵循现有模型约定；数据库继续使用 SQLite

## Capabilities

### New Capabilities

- `enum-crud-api`: EntityType / ActionType / SoundType / ResponseAction 四个 AI 检测枚举表的 CRUD API 与 Service，支持后续扩展新的检测类型
- `alert-group-crud-api`: AlertGroup 告警分组的 CRUD API 与 Service，含独立 ResponseAction 枚举管理路由 + 嵌套绑定/解绑路由
- `exception-crud-api`: ExceptionDef 异常规则的 CRUD API 与 Service，含 severity + group_id 管理 + 多对多绑定 EntityType/ActionType/SoundType
- `event-query-api`: SituationEvent 事件日志的只读查询 API 与 Service，支持按 view 过滤、按时间范围过滤、按 exception 分组 count 聚合、按时间段趋势统计

### Modified Capabilities

<!-- 所有现有 Spec 均为 Model/Repo 层定义，本次新增的 Service/Schema/API 层为全新能力，无需修改已有 Spec -->

## Impact

- **Service 层**: 新增 `src/service/alert_task.py + alert_module/`、`src/service/exception_task.py + exception_module/`、`src/service/event_task.py`
- **Schema 层**: 新增 `src/schema/http/enum_types.py`、`src/schema/http/alert.py`、`src/schema/http/exception.py`、`src/schema/http/event.py`
- **API 层**: 新增 `src/network/api/enum_types.py`、`src/network/api/alert.py`、`src/network/api/exception.py`、`src/network/api/event.py`
- **路由注册**: 更新 `src/network/api/__init__.py` 汇总新路由
- **现有代码**: 不修改任何已有 Model / Repo / Config，纯增量
