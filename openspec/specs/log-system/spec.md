# Log System

**Purpose:** 定义统一分类日志系统 — LogEntry 模型 + 写入 Service + 查询 API。

## Requirements

### Requirement: LogEntry 统一日志模型
系统 SHALL 定义 `LogEntry` 模型，映射到 `log_entries` 表，存储分类日志记录。

- `id`: 自增主键
- `log_type`: 日志类型枚举（DEVICE / OPERATION / RECOGNITION / ALERT / SYSTEM）
- `operator_id`: 操作人 ID FK→users（可空，系统自动事件无操作人）
- `view_id`: 关联监控视图 ID FK→monitor_views（可空）
- `event_id`: 关联异常事件 ID FK→situation_events（可空）
- `severity`: 严重级别（可空，非告警类日志可不设）
- `summary`: 一句话摘要（String 256），用于列表展示
- `details_json`: JSON 扩展字段（Text），存各类差异化信息
- `created_at`: 时间戳

#### Scenario: 记录设备状态日志
- **WHEN** Node 连接断开
- **THEN** 系统写入 DEVICE 类型日志，details_json 包含 device_type/device_id/event

#### Scenario: 记录用户操作日志
- **WHEN** 管理员删除一个命名人物
- **THEN** 系统写入 OPERATION 类型日志，details_json 包含 action/target_type/target_id/target_name，operator_id 指向操作人

#### Scenario: 记录告警处置日志
- **WHEN** 安全员确认一个告警事件
- **THEN** 系统写入 ALERT 类型日志，details_json 包含 action/event_id/comment，operator_id 指向处置人

### Requirement: 日志只读查询
系统 SHALL 提供日志的只读查询 API，不开放创建/修改/删除端点。

- `GET /api/v1/logs` — 日志列表（分页：page, page_size）
- `GET /api/v1/logs/{id}` — 单条日志详情

> **注意**：按 log_type/时间范围/severity 筛选与统计端点（`/logs/stats`）计划在后续迭代中实现。
