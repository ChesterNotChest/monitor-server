# Fence Entry Delay

## Purpose

围栏触发 ENTERED 状态前可配置停留秒数。为 0 时进入即触发；为 X 秒时，需连续停留 X 秒才触发 ENTERED。替代现有的 `dwell_time` + `density` 密度计算逻辑。

## ADDED Requirements

### Requirement: entry_delay_seconds on ElectronicFence

`ElectronicFence` 模型 SHALL 包含 `entry_delay_seconds` 字段（秒，整数，默认 0）。
当 `entry_delay_seconds=0` 时，YOLO 框碰触围栏的**首帧**即触发 ENTERED。
当 `entry_delay_seconds=X` 时，YOLO 框必须**连续**在围栏内 X 秒后才触发 ENTERED。

#### Scenario: Immediate entry

- **WHEN** `entry_delay_seconds=0` 且 YOLO 框首次碰到围栏
- **THEN** 立即发布 ENTERED 事件

#### Scenario: Delayed entry

- **WHEN** `entry_delay_seconds=5` 且人物进入围栏
- **THEN** 连续 5 秒在围栏内后发布 ENTERED 事件
- **AND** 若 5 秒内人物离开，不触发 ENTERED

### Requirement: entry_delay replaces density-based gate

fence_engine SHALL 使用 `entry_delay_seconds` 替代现有的 `dwell_time` + `density` 组合。
保持 `leave_frames` 用于离开判定（连续 N 帧不在围栏内判定为离开）。

#### Scenario: Leave detection unchanged

- **WHEN** `leave_frames=5` 且人物离开围栏
- **THEN** 连续 5 帧不在围栏内后发布 EXITED 事件
