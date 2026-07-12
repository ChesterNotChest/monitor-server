## ADDED Requirements

### Requirement: RECORDING 事件订阅者桥接告警引擎到录制模块

系统 SHALL 在 EventBus 上注册 `RECORDING` 事件类型的订阅者。当 AlertEngine 发布 `RECORDING` 事件时，订阅者 SHALL 调用 `replay_task.alert_triggered(view_id, db)`，使用独立的数据库会话。

#### Scenario: 收到 RECORDING 事件触发录制

- **WHEN** AlertEngine 向 EventBus 发布 `{"action": "keep_alive", "view_id": N}` 的 RECORDING 事件
- **THEN** 订阅者调用 `replay_task.alert_triggered(N, db)` 创建或延续录制会话

#### Scenario: 订阅者异常不影响告警引擎

- **WHEN** 录制订阅者处理 RECORDING 事件时抛出异常
- **THEN** EventBus 捕获异常并记录日志，不影响 AlertEngine 或其他订阅者

#### Scenario: 订阅者随管线生命周期注册和注销

- **WHEN** `start_pipeline(view_id)` 被调用
- **THEN** 若尚未注册，系统向 EventBus 注册 RECORDING 订阅者
- **WHEN** `stop_pipeline(view_id)` 被调用
- **THEN** 若该 view_id 是最后一个活跃管线，系统从 EventBus 注销 RECORDING 订阅者
