## ADDED Requirements

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

#### Scenario: 按日志类型过滤查询
- **WHEN** 客户端 `GET /api/v1/logs?log_type=DEVICE`
- **THEN** 系统返回设备类日志分页列表

#### Scenario: 按时间范围过滤查询
- **WHEN** 客户端 `GET /api/v1/logs?start=...&end=...`
- **THEN** 系统仅返回该时间区间内的日志

#### Scenario: 多条件组合过滤
- **WHEN** 客户端 `GET /api/v1/logs?view_id=3&log_type=RECOGNITION&start=...`
- **THEN** 系统返回符合所有条件的日志

### Requirement: 日志统计
系统 SHALL 提供按 log_type 或 severity 分组的日志数量统计端点。

#### Scenario: 按日志类型分组统计
- **WHEN** 客户端 `GET /api/v1/logs/stats?group_by=log_type`
- **THEN** 系统返回 `[{"log_type": "DEVICE", "count": 15}, ...]`

#### Scenario: 按严重级别分组统计
- **WHEN** 客户端 `GET /api/v1/logs/stats?group_by=severity`
- **THEN** 系统返回 `[{"severity": "CRITICAL", "count": 8}, ...]`
