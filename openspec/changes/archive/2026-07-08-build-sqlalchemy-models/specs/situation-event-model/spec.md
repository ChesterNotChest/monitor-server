## ADDED Requirements

### Requirement: 事件表定义
系统 SHALL 定义 `SituationEvent` 模型，映射到 `situation_events` 表，记录在特定监控视图中发生的异常事件。

- `id`: 自增主键（Integer）
- `view_id`: 外键关联 `monitor_views.id`（Integer，非空，索引）
- `exception_id`: 外键关联 `exceptions.id`（Integer，非空，索引）
- `timestamp`: 事件发生时间（DateTime，非空，默认 UTC now）

#### Scenario: 记录异常事件
- **WHEN** 插入记录指定 `view_id`、`exception_id` 和 `timestamp`
- **THEN** 系统持久化该异常事件

#### Scenario: 按监控视图查询历史事件
- **WHEN** 通过 `view_id` 查询并可按时间范围过滤
- **THEN** 系统返回该视图下所有符合条件的异常事件记录
