# Monitor View Model

**Purpose:** 定义监控视图数据模型，组合视频与音频设备形成完整监控画面。

## Requirements

### Requirement: 监控视图表定义
系统 SHALL 定义 `MonitorView` 模型，映射到 `monitor_views` 表，组合视频与音频设备形成一个完整的监控视图。

- `id`: 自增主键（Integer）
- `video_id`: 外键关联 `video_devices.id`（Integer，非空，索引）
- `audio_id`: 外键关联 `audio_devices.id`（Integer，可空，索引）
- `cache_path`: 缓存文件路径（String，可空）

#### Scenario: 创建包含完整音视频的监控视图
- **WHEN** 插入记录同时指定 `video_id` 和 `audio_id`
- **THEN** 系统建立对视频设备和音频设备的双向外键关联

#### Scenario: 创建仅视频的监控视图
- **WHEN** 插入记录仅指定 `video_id`，`audio_id` 为空
- **THEN** 系统成功创建仅含视频的监控视图（允许无音频的监控场景）
