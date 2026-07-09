## Why

AI 管线文档 §8 定义了缓存区与触发录制的需求：告警触发时，从环形缓冲区取此前 N 秒的加框前原始帧开始录制，持续进行直到连续 M 秒无新告警才停止。录制文件按 `{cache_path}/view_{id}_{timestamp}.flv` 命名。`MonitorView.cache_path` 字段已就绪。需要补上环形缓冲区、持续录制引擎和回放查询 API。

不做截图、不做处置状态机（后续独立 Change）。AI 引擎接入时会调录制服务——只管存和读，不做收口。

## What Changes

- 新增 `FrameRingBuffer`：环形缓冲区，存储加框前原始帧（支持 CACHE_DURATION_SECONDS 配置）
- 新增 `RecordingSession`：持续录制会话——告警触发时开始，每次新告警重置静默计时器，连续 N 秒无告警则停止并写文件
- 录制文件格式：FLV，路径 `{MonitorView.cache_path}/view_{id}_{timestamp}.flv`
- 配置项：`CACHE_DURATION_SECONDS`(30s)、`RECORD_STOP_SILENCE_SECONDS`(60s)
- 新增 `Recording` 记录表（view_id, file_path, start_time, end_time）供查询
- 新增回放查询 API：按 view_id + 时间范围查录制文件列表 + 流式读取 flv 文件

## Capabilities

### New Capabilities

- `clip-replay`: 持续录制引擎 — 环形缓冲区 + RecordingSession + 回放查询 + flv 文件流式读取

### Modified Capabilities

<!-- 无 — 纯增量。不修改 SituationEvent。MonitorView.cache_path 已就绪无需改动 -->

## Impact

- **新增**: `models/recording.py` — Recording 记录模型
- **新增**: `service/replay_module/ring_buffer.py` — 环形缓冲区
- **新增**: `service/replay_module/recorder.py` — 录制引擎（RecordingSession 管理）
- **新增**: `service/replay_task.py` — 门户函数（alert_triggered / recording lifecycle）
- **新增**: `schema/http/replay.py` — RecordingResponse
- **新增**: `network/api/replay.py` — GET /views/{id}/recordings + GET /recordings/{id}/stream
- **新增**: `config.py` — CACHE_DURATION_SECONDS / RECORD_STOP_SILENCE_SECONDS
- **使用已有**: `MonitorView.cache_path` — 录制文件存储根目录
- **不修改**任何现有代码
