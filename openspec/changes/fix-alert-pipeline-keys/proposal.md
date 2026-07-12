## Why

告警已实时推送到前端（YOLO框可见），但两个关键功能缺失：(1) 同一实体同一track ID会在每个检测帧都触发告警，需要按track+类型去重，且冷却时间应可由用户在网站配置；(2) 点击"查看回放"显示404——录制功能从未在告警触发时启动，`RECORDING`事件仅在冷却期发布而非首次告警，`SituationEvent.recording_id`也从未被设置。

## What Changes

### 告警去重与可配置冷却
- **AlertEngine**：去重key从 `(view_id, exception_id)` 扩展为 `(view_id, exception_id, track_id)`，同一人同一类型告警在冷却期内只触发一次
- **ExceptionDef模型 + schema**：新增 `cooldown_seconds` 字段（默认30），API支持CRUD
- **前端**：异常规则编辑页新增冷却时间输入框

### 录制回放修复
- **AlertEngine._trigger()**：首次告警触发时也发布 `RECORDING` 事件（start），冷却期内发布 `keep_alive`
- **replay_task.alert_triggered()**：创建Recording后回填 `SituationEvent.recording_id`
- **view_task.py**：`_on_recording` 订阅者区分 `start`/`keep_alive`，首次调用 `alert_triggered()`

## Capabilities

### New Capabilities
- `alert-track-dedup`: 按track ID去重，每个entity+track在冷却期内只告警一次
- `alert-cooldown-config`: 用户可在网站设置异常规则的冷却时间

### Modified Capabilities
- `alert-api`: `ExceptionDef` CRUD新增 `cooldown_seconds` 字段
- `clip-replay`: 录制在首次告警时启动（修复 `RECORDING` 发布时机），`recording_id` 回填 `SituationEvent`

## Impact

- `src/service/alert_module/engine.py` — 去重key改为三维 + 首次告警发布RECORDING start
- `src/models/exception.py` — `ExceptionDef` 新增 `cooldown_seconds` 列
- `src/schema/http/` — 相关schema新增字段
- `src/service/replay_task.py` — `alert_triggered` 回填recording_id
- `src/service/vision_task.py` — `_on_recording` 处理 start/keep_alive
- `monitor-web` — 异常编辑页新增冷却时间输入
