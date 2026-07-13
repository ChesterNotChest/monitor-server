# Alert Track Dedup

## Purpose

同一track ID + 同一异常规则在冷却期内只触发一次告警，避免同一目标每一帧都产生重复告警。

## ADDED Requirements

### Requirement: Dedup key includes track_id

AlertEngine 去重 SHALL 使用 `(view_id, exception_id, track_id)` 三元组，
而非当前的 `(view_id, exception_id)` 二元组。

#### Scenario: Same person triggers once

- **WHEN** track_id=5 的 person 持续出现在画面中
- **THEN** 冷却期内 `(view=1, exception=1, track=5)` 只触发一次告警

#### Scenario: Different persons each trigger

- **WHEN** track_id=5 和 track_id=7 的两个人同时出现
- **THEN** 两者各自触发一次告警（不同 track_id 独立冷却）

### Requirement: Alert payload includes track_id

WSS 推送和 REST API 返回的告警 SHALL 包含 `track_id` 字段。

#### Scenario: Alert with track_id

- **WHEN** 告警触发
- **THEN** 前端收到的告警消息包含 `track_id` 值
