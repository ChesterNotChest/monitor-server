# Clip Replay (Delta)

## MODIFIED Requirements

### Requirement: Recording starts on first alert trigger

AlertEngine 首次触发告警时 SHALL 发布 `RECORDING` 事件（`action: "start"`）。
`replay_task` SHALL 在收到 `start` 事件时创建录制会话。

#### Scenario: Recording starts on initial alert

- **WHEN** AlertEngine 首次匹配到异常规则并创建 SituationEvent
- **THEN** `RECORDING` 事件发布到 EventBus
- **AND** `replay_task` 启动录制会话
- **AND** SituationEvent 的 `recording_id` 被设置为新创建的 `Recording.id`

### Requirement: Keep-alive during cooldown

冷却期内的重复告警 SHALL 继续发布 `RECORDING` 事件（`action: "keep_alive"`）
以延长录制会话的静默计时器。

#### Scenario: Keep-alive extends recording

- **WHEN** 同一 track 在冷却期内再次触发匹配
- **THEN** 录制会话的静默计时器重置
- **AND** 录制持续到最后一条告警后的 `RECORD_STOP_SILENCE_SECONDS`
