# AI Model Capability — Delta

## ADDED Requirements

### Requirement: 电子围栏多状态检测
系统 SHALL 支持电子围栏的三态检测模型：NOT_ENTERED、ENTERED、TOO_CLOSE。检测引擎每帧评估所有 Track 与所有围栏的空间关系。

#### Scenario: 三态状态机
- **WHEN** Track 靠近围栏安全距离区
- **THEN** 状态机按 NOT_ENTERED → TOO_CLOSE → ENTERED 路径演进；离开时按 ENTERED → NOT_ENTERED 或 TOO_CLOSE → NOT_ENTERED 路径返回

#### Scenario: entry_delay 计时替代 density
- **WHEN** 围栏检测引擎评估进入条件
- **THEN** 使用 `frame_timestamp - entry_start >= entry_delay_seconds` 判定，不再使用 density 密度窗口计算

#### Scenario: FENCE 事件键名对齐
- **WHEN** 围栏检测引擎发布事件到 EventBus FENCE topic
- **THEN** payload 同时包含 `fence_event_ids`（数组）和 `fences`（详细列表），与 AlertEngine 期望的键名一致
