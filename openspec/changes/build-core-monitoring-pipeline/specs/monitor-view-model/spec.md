# Monitor View Model

**Purpose:** 监控视图数据模型的变更——audio_id 改为 non-nullable。

## MODIFIED Requirements

### Requirement: 监控视图表定义

系统 SHALL 定义 `MonitorView` 模型，映射到 `monitor_views` 表，组合视频与音频设备形成一个完整的监控视图。

- `id`: 自增主键（Integer）
- `video_id`: 外键关联 `video_devices.id`（Integer，非空，索引）
- `audio_id`: 外键关联 `audio_devices.id`（Integer，非空，索引）
- `cache_path`: 缓存文件路径（String，可空）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 创建包含完整音视频的监控视图

- **WHEN** 插入记录同时指定 `video_id` 和 `audio_id`
- **THEN** 系统建立对视频设备和音频设备的双向外键关联

## REMOVED Requirements

### Requirement: 创建仅视频的监控视图

**Reason**: View 必须同时包含音频和视频设备以形成完整监控画面。后续 AI 处理管线需要在 Server 侧同时处理音视频帧。
**Migration**: 已存在的纯视频 View 需在变更前补充 audio_id，或删除重建。
