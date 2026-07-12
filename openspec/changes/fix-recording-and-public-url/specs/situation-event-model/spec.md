## MODIFIED Requirements

### Requirement: 事件表定义
系统 SHALL 定义 `SituationEvent` 模型，映射到 `situation_events` 表，记录在特定监控视图中发生的异常事件。

- `id`: 自增主键（Integer）
- `view_id`: 外键关联 `monitor_views.id`（Integer，非空，索引）
- `exception_id`: 外键关联 `exceptions.id`（Integer，非空，索引）
- `recording_id`: 关联录制记录 ID（Integer，可空，外键关联 `recordings.id`）
- `timestamp`: 事件发生时间（DateTime，非空，默认 UTC now）

#### Scenario: 记录异常事件
- **WHEN** 插入记录指定 `view_id`、`exception_id` 和 `timestamp`
- **THEN** 系统持久化该异常事件

#### Scenario: 按监控视图查询历史事件
- **WHEN** 通过 `view_id` 查询并可按时间范围过滤
- **THEN** 系统返回该视图下所有符合条件的异常事件记录

#### Scenario: 事件含录制关联
- **WHEN** AI 告警引擎触发事件且录制会话已启动
- **THEN** 系统在 SituationEvent 中记录 `recording_id`，关联到对应的录制文件

## ADDED Requirements

### Requirement: EventResponse 暴露 recording_id

`EventResponse` Pydantic schema SHALL 包含 `recording_id: int | None` 字段。该字段 SHALL 从 `SituationEvent` ORM 对象的 `recording_id` 属性自动映射（`from_attributes=True`）。

#### Scenario: 前端获取含录制 ID 的事件

- **WHEN** 前端请求 `GET /api/v1/events/{id}` 且该事件关联了录制
- **THEN** 响应包含 `recording_id` 字段，值为录制记录 ID
- **AND** 前端可通过此 ID 调用 `GET /api/v1/recordings/{id}/stream` 播放回放

#### Scenario: 事件无录制关联

- **WHEN** 前端请求 `GET /api/v1/events/{id}` 且该事件未关联录制
- **THEN** 响应中 `recording_id` 为 `null`
