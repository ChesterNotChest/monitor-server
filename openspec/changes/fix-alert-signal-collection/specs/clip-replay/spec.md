# Clip Replay (delta)

## ADDED Requirements

### Requirement: 录制生命周期 debug 日志
系统 SHALL 在 RecordingSession 和 replay_task 关键生命周期点输出 INFO 级别日志：

- 录制启动时：view_id, recording_id, max_duration, wind_down
- 新告警 keep_alive 时：view_id, recording_id
- wind_down 开始时：view_id, recording_id, wind_down 秒数
- wind_down 结束时（停止录制）：view_id, recording_id, 录制总时长
- max_duration 触发停止时：view_id, recording_id, 录制总时长
- 告警结束触发录制停止时：view_id, recording_id
- 冷却重置时：view_id, exc_id, track_id

#### Scenario: 录制启动日志
- **WHEN** `alert_triggered(action="start")` 创建新 RecordingSession
- **THEN** 日志输出 `[Replay] START view=1 rec=42 max_dur=30s wind_down=15s`

#### Scenario: wind_down 开始日志
- **WHEN** `on_alert_end()` 被调用，wind_down 倒计时开始
- **THEN** 日志输出 `[Replay] WIND_DOWN view=1 rec=42 wait=15s`

#### Scenario: max_duration 触发停止日志
- **WHEN** 录制达到 `max_duration` 秒被强制停止
- **THEN** 日志输出 `[Replay] MAX_DUR stop view=1 rec=42 elapsed=30s`

#### Scenario: 冷却重置日志
- **WHEN** 告警结束触发冷却重置（`_end_inactive`）
- **THEN** 日志输出 `[AlertEngine] cooldown RESET key=(1,2,3)`
