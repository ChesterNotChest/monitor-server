## Why

异常事件触发时，需要保留事件前后的录像片段用于回放追溯。目前 `SituationEvent` 只记录时间戳，没有媒体关联。需要补上 clip 存储能力和时间轴回放查询。

不做截图、不做处置状态机（后续独立 Change）。AI 引擎后续接入时会直接调用 clip 存储接口——只管存和读，不做收口。

## What Changes

- `SituationEvent` 扩展 `clip_path` 字段（录像片段相对路径）
- 新增 `ClipService`：环形缓冲区 + "精彩回放"式触发写入
  - `start(view_id)` — 开始缓冲（View 创建时调）
  - `trigger(view_id, event_id)` — 从 (now - CLIP_PRE_SECONDS) 开始取帧，继续录 CLIP_POST_SECONDS，写文件到 `clips/event_{id}.mp4`，返回路径
  - `stop(view_id)` — 停止缓冲（View 删除时调）
- 可配置参数：`CLIP_BUFFER_SECONDS`(30s) / `CLIP_PRE_SECONDS`(5s) / `CLIP_POST_SECONDS`(10s)
- 新增时间轴查询 API：`GET /views/{id}/timeline`、`GET /events/{id}/clip`

## Capabilities

### New Capabilities

- `clip-replay`: 录像片段存储与回放 — 环形缓冲区 + clip 写入 + timeline 查询 + clip 文件流式读取

### Modified Capabilities

- `situation-event-model`: `SituationEvent` 新增 `clip_path` 字段（String 512，可空），指向录像片段相对路径

## Impact

- **修改**: `models/situation_event.py` — 新增 `clip_path` 字段
- **新增**: `service/replay_module/ring_buffer.py` — 帧环形缓冲区
- **新增**: `service/replay_module/clip.py` — clip 写入服务
- **新增**: `service/replay_task.py` — 门户（start/stop/trigger）
- **新增**: `schema/http/replay.py` — TimelineItem / ClipResponse
- **新增**: `network/api/replay.py` — GET /views/{id}/timeline + GET /events/{id}/clip
- **新增**: `config.py` — CLIP_BUFFER_SECONDS / CLIP_PRE_SECONDS / CLIP_POST_SECONDS
- **不修改**任何 Service/API 收口逻辑
