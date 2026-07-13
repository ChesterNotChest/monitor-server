# Optional Audio View

**Purpose:** View 创建时音频设备改为可选，无音频时自动跳过 YAMNet。

## ADDED Requirements

### Requirement: audio_id 改为可选
系统 SHALL 将 `MonitorView.audio_id` 字段改为 `nullable=True`。`POST /api/v1/views/` 的 `audio_id` 参数改为 optional。

#### Scenario: 创建纯视频 View
- **WHEN** 用户 POST `{video_id:1}` 不传 audio_id
- **THEN** 系统创建 View（audio_id=NULL），返回 201

#### Scenario: 无音频时跳过 YAMNet
- **WHEN** View 的 audio_id 为 NULL 时启动管线
- **THEN** 系统不启动 YamnetRunner，S 信号始终为 ∅
