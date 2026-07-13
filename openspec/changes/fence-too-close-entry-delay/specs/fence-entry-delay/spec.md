# Fence Entry Delay

**Purpose:** 可配置停留秒数——替代 density 密度计算，提供直观的"停留 N 秒后触发 ENTERED"判定。

## Requirements

### Requirement: 停留延时配置
系统 SHALL 允许为电子围栏配置 `entry_delay_seconds` 秒数（默认 0 = 进入即触发 ENTERED，>0 = 连续停留 N 秒后触发）。

#### Scenario: 立即触发
- **WHEN** 创建围栏时设置 `entry_delay_seconds=0`
- **THEN** Track 进入围栏的同一帧立即触发 ENTERED 事件

#### Scenario: 延时触发
- **WHEN** 创建围栏时设置 `entry_delay_seconds=3` 且 Track 在 `t=1.0` 首次进入围栏
- **THEN** 在 `t >= 4.0`（即连续停留满 3 秒）时触发 ENTERED 事件

#### Scenario: 中途离开
- **WHEN** 创建围栏时设置 `entry_delay_seconds=3` 且 Track 在 `t=1.0` 进入、`t=2.0` 离开
- **THEN** 计时器清零，不触发 ENTERED。Track 再次进入时重新计时

### Requirement: 时间戳计时器
系统 SHALL 使用帧时间戳（`frame_timestamp`，Unix 秒）而非帧计数来判定停留时长。

#### Scenario: 帧率无关
- **WHEN** 输入帧率从 25fps 变为 15fps
- **THEN** `entry_delay_seconds=3` 的判定结果不受影响——始终是 3 秒后触发，而非固定帧数后触发

### Requirement: 退出判定独立
系统 SHALL 继续使用 `leave_frames`（离开帧数）判定 EXITED，与 `entry_delay_seconds` 的进入判定逻辑互相独立。

#### Scenario: 进入延时 + 退出帧数配合
- **WHEN** 围栏配置 `entry_delay_seconds=3`、`leave_frames=5`
- **THEN** Track 需连续停留 3 秒后触发 ENTERED；离开围栏后连续 5 帧不在围栏内触发 EXITED。两套计时/计数机制独立运行，不互相干扰
