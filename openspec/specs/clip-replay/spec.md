# Clip Replay

**Purpose:** 定义持续录制引擎 — 环形缓冲区 + RecordingSession + 回放查询 + flv 文件流式读取。

## Requirements

### Requirement: 环形缓冲区
系统 SHALL 提供帧级环形缓冲区，每个 MonitorView 一个实例，存储加框前原始帧，缓存时长可配置。

#### Scenario: 创建缓冲区并写入帧
- **WHEN** 调用 `start_buffer(view_id)` 后持续调用 `push_frame(view_id, frame_bytes)`
- **THEN** 缓冲区保留最近 `CACHE_DURATION_SECONDS` 秒的帧，超出部分自动丢弃

#### Scenario: 停止缓冲区
- **WHEN** 调用 `stop_buffer(view_id)`
- **THEN** 缓冲区清空并释放内存

#### Scenario: 缓冲区溢出
- **WHEN** 帧写入速率超过缓冲区容量
- **THEN** 旧帧被丢弃（FIFO），缓冲区始终保留最新帧

### Requirement: 持续录制引擎
系统 SHALL 提供持续录制能力：告警触发时开始录制，从缓冲区获取此前 `CACHE_DURATION_SECONDS` 秒的历史帧，持续写入新帧，连续 `RECORD_STOP_SILENCE_SECONDS` 秒无新告警则停止并生成 flv 文件。

#### Scenario: 首次告警触发开始录制
- **WHEN** AI 告警引擎调用 `alert_triggered(view_id)` 且该 View 当前无活跃录制
- **THEN** 系统创建 RecordingSession，从缓冲区 dump 此前历史帧，开始持续写入新帧

#### Scenario: 密集告警重置静默计时
- **WHEN** 录制进行中再次调用 `alert_triggered(view_id)`（新告警触发）
- **THEN** 系统重置静默计时器为 `RECORD_STOP_SILENCE_SECONDS`，录制继续

#### Scenario: 静默超时停止录制
- **WHEN** 录制进行中且连续 `RECORD_STOP_SILENCE_SECONDS` 秒无新的 `alert_triggered` 调用
- **THEN** 系统写 flv 文件到 `{cache_path}/view_{id}_{timestamp}.flv`，创建 Recording 记录，释放缓冲区引用

#### Scenario: 录制中缓冲区无历史帧
- **WHEN** 缓存区刚创建不久（不足 `CACHE_DURATION_SECONDS` 秒）即触发录制
- **THEN** 系统取所有可用历史帧，从当前帧开始录制

### Requirement: Recording 记录
系统 SHALL 定义 `Recording` 模型记录每次录制会话，与事件表解耦。

- `id`: 自增主键
- `view_id`: FK→monitor_views
- `file_path`: flv 文件相对路径
- `start_time`: 录制开始时间
- `end_time`: 录制结束时间
- `created_at`: 记录创建时间

#### Scenario: 录制完成写入记录
- **WHEN** 一段录制停止并生成 flv 文件
- **THEN** 系统写入 Recording 记录（view_id, file_path, start_time, end_time）

### Requirement: 录制文件查询
系统 SHALL 提供按 View 和时间范围查询录制文件的 API。

#### Scenario: 查询某画面某时段的录制
- **WHEN** 客户端 `GET /api/v1/views/3/recordings?start=2026-01-01T00:00&end=2026-01-01T23:59`
- **THEN** 系统返回该时段内所有 Recording 列表

#### Scenario: 无录制文件
- **WHEN** 查询的时段内没有录制记录
- **THEN** 系统返回空列表

### Requirement: 录制文件流式读取
系统 SHALL 提供 flv 录制文件的流式读取 API。

#### Scenario: 获取存在的录制文件
- **WHEN** 客户端 `GET /api/v1/recordings/1/stream`
- **THEN** 系统返回 flv 文件流（Content-Type: video/x-flv）

#### Scenario: 录制文件不存在
- **WHEN** 文件路径存在但磁盘文件已被删除
- **THEN** 系统返回 404
