# YAMNet Inference

**Purpose:** 独立音频分支——YAMNet AudioSet 521 类音频分类 → SoundType 枚举事件。

## ADDED Requirements

### Requirement: 音频流拉取

系统 SHALL 通过 FFmpeg 子进程从 SRS 拉取 raw audio RTMP 流，解为 16kHz 单声道 float32 numpy array。每 0.96 秒（YAMNet 输入窗口）SHALL 推理一次。

#### Scenario: 音频推理窗口

- **WHEN** FFmpeg 持续输出 16kHz float32 音频样本
- **THEN** 每累积 0.96 秒样本量送 YAMNet 推理一次

### Requirement: SoundType 映射

系统 SHALL 将 YAMNet 输出的 AudioSet 521 类概率映射到 `ai-model-capability` spec 定义的 15 类 SoundType。概率 > `YAMNET_THRESHOLD`（默认 0.5）的类别 SHALL 产出 SoundType 枚举事件。

#### Scenario: 检测枪声

- **WHEN** YAMNet 输出 `Gunshot` 概率 0.85
- **THEN** 产出 `SoundType.GUNSHOT (1)` 事件

#### Scenario: 无声

- **WHEN** 所有 15 类概率 < 0.5
- **THEN** 产出 `SoundType.SILENCE (15)` 事件

### Requirement: YAMNet 状态机

YAMNet SHALL 维护 IDLE（未拉流）→ ACTIVE（正常推理）→ ERROR（拉流失败）。音频流中断 SHALL 自动重连。

#### Scenario: 音频流中断

- **WHEN** RTMP 音频流中断
- **THEN** 停止推理，自动重连拉流，重连后恢复
