# AI Model Capability (Delta)

## MODIFIED Requirements

### Requirement: SlowFast publishes ACTION events to EventBus

SlowFast 行为识别结果 SHALL 通过 EventBus 发布 ACTION 事件，
键名为 `action_type_ids`，值为检测到的行为类型 ID 列表。

#### Scenario: SlowFast action published

- **WHEN** SlowFast 检测到行为（如 running、fighting）
- **THEN** EventBus 收到 `ACTION` 事件，包含 `{"action_type_ids": [int, ...]}`

### Requirement: YAMNet publishes SOUND events with correct key

YAMNet 音频分类结果 SHALL 通过 EventBus 发布 SOUND 事件，
键名为 `sound_type_ids`（非 `sound_type`），值为检测到的声音类型 ID 列表。

#### Scenario: YAMNet sound published

- **WHEN** YAMNet 检测到声音（如 glass_break、scream）
- **THEN** EventBus 收到 `SOUND` 事件，包含 `{"sound_type_ids": [int, ...]}`
