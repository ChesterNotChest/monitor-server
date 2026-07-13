## Context

告警已推送成功，但有两个缺失：按track去重+可配置冷却 + 录制回放。

## Goals / Non-Goals

**Goals:**
- 同track+同异常在冷却期内只告警一次
- 冷却时间可在异常规则中配置
- 首次告警触发录制，回放可用

**Non-Goals:**
- 不改录制文件存储方式
- 不改前端播放器

## Decisions

### Decision 1: 三维去重key

`(view_id, exception_id, track_id)` 替代 `(view_id, exception_id)`。

AlertEngine._trigger 接收 `track_id` 参数。YOLO检测的entity事件需携带track_id（从ByteTrack获取）。

### Decision 2: cooldown_seconds 存储在 ExceptionDef

新增DB列 `cooldown_seconds INTEGER DEFAULT 30`。为 null 或 0 时回退到全局 `ALERT_COOLDOWN`。

### Decision 3: RECORDING 事件在首次触发时发布

在 `_trigger()` 中，即使不处于冷却期，创建 SituationEvent 后也发布 `RECORDING` 事件（action: "start"）。`replay_task.alert_triggered()` 创建Recording后回填 `situation_event.recording_id`。

### Decision 4: track_id 从 EventBus 事件中提取

YOLO 的 `entities` 字典包含 `track_id`（由 ByteTrack 在 Part B 中填充）。AlertEngine 从事件payload中提取 `track_id`。

## Risks

- [Risk] 旧ExceptionDef无cooldown_seconds → ALTER TABLE加默认值
- [Risk] track_id在YOLO事件中可能不存在（ByteTrack未运行时） → 降级为 -1（无track去重）
