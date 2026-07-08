## ADDED Requirements

### Requirement: 响应动作枚举表定义
系统 SHALL 定义 `ResponseAction` 模型，映射到 `response_actions` 表，存储异常触发后的响应动作类型。

- `id`: 自增主键（Integer）
- `name`: 响应动作名称（String，唯一，非空），如 `trigger_recording`、`send_notification`、`activate_alarm` 等

#### Scenario: 注册响应动作类型
- **WHEN** 向 `response_actions` 表插入动作名称
- **THEN** 系统持久化该响应动作枚举值

#### Scenario: 查询所有响应动作
- **WHEN** 查询 `response_actions` 全表
- **THEN** 系统返回所有已注册的响应动作列表

### Requirement: 告警分组-响应多对多关联
系统 SHALL 定义 `alert_group_responses` 关联表，建立告警分组与响应动作的多对多关系。

- `group_id`: 外键关联 `alert_groups.id`
- `response_id`: 外键关联 `response_actions.id`

#### Scenario: 关联告警分组与响应动作
- **WHEN** 向 `alert_group_responses` 插入 `group_id` 与 `response_id`
- **THEN** 系统建立该告警分组与该响应动作的关联，同一分组可触发多个响应动作
