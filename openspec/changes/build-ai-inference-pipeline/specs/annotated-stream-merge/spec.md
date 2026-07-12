# Annotated Stream Merge

**Purpose:** FFmpeg 合并标注 video + 原始 audio → 推 SRS 成品 View 流。

## ADDED Requirements

### Requirement: 合并管线

系统 SHALL 使用 FFmpeg 子进程合并标注视频帧（pipe 输入）和原始音频（RTMP pull）。输出 SHALL 推送到 `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/view/{view_id}`。

#### Scenario: 合并推流

- **WHEN** 标注帧持续写入 FFmpeg stdin pipe
- **AND** 原始音频从 SRS 正常拉流
- **THEN** FFmpeg 输出 RTMP 推送到 SRS View 成品流 URL

### Requirement: 音频延迟对齐

标注管线引入约 80-100ms 延迟。首版 SHALL 不做音频延迟同步。

#### Scenario: 默认不同步

- **WHEN** 标注帧比原始音频晚 80ms
- **THEN** 合并后音画偏差 < 200ms，人耳无感知
