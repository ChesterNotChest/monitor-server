## ADDED Requirements

### Requirement: 告警触发写入结构化日志

系统 SHALL 在告警引擎创建新的 `SituationEvent` 后写入一条 `LogEntry`，使 Web 日志中心可以展示真实告警产生记录。

#### Scenario: 新告警事件产生日志

- **WHEN** `AlertEngine` 匹配异常规则并创建新的 `SituationEvent`
- **THEN** 系统写入一条 `LogEntry`
- **AND** `log_type` 为 `LogType.ALERT`
- **AND** `view_id` 指向发生告警的监控视图
- **AND** `event_id` 指向新创建的 `SituationEvent`
- **AND** `severity` 等于异常定义的严重级别
- **AND** `summary` 包含告警触发和异常名称

#### Scenario: 日志详情包含告警上下文

- **WHEN** 告警触发日志被写入
- **THEN** `details_json` SHALL 包含 `action=triggered`、`event_id`、`view_id`、`exception_id`、`exception_name`、`severity` 和 `recording_id`
