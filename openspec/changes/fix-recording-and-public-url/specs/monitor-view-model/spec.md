## MODIFIED Requirements

### Requirement: 监控视图表定义
系统 SHALL 定义 `MonitorView` 模型，映射到 `monitor_views` 表，组合视频与音频设备形成一个完整的监控视图。

- `id`: 自增主键（Integer）
- `video_id`: 外键关联 `video_devices.id`（Integer，非空，索引）
- `audio_id`: 外键关联 `audio_devices.id`（Integer，非空，索引）
- `name`: 视图名称（String，可空，最长 128 字符）
- `cache_path`: 缓存文件路径（String，可空）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 创建包含完整音视频的监控视图
- **WHEN** 插入记录同时指定 `video_id` 和 `audio_id`
- **THEN** 系统建立对视频设备和音频设备的双向外键关联

#### Scenario: 创建带名称的监控视图
- **WHEN** 创建 View 时提供 `name`
- **THEN** 系统持久化该名称
- **WHEN** 未提供 `name`
- **THEN** `name` 为 `null`，前端展示降级名称 "视图 N"
