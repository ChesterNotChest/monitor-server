## Why

前面的 `align-streaming-api` 修复了 View 查询不返回 `flv_url` 的问题，但端到端追踪发现录制/回放链路完全断裂：`replay_task.push_frame()` 和 `start_buffer()` 从未被调用，环形缓冲区始终为空，EventBus 的 `RECORDING` 主题没有订阅者。同时 `SRS_PUBLIC_HOST` 未配置，返回给 Web 的 URL 全是 `127.0.0.1`。

Web 端最新代码已切换到 WebRTC WHEP 播放（LiveMonitor 和 FenceEditor 均消费 `webrtc_url`），EventReplay 页面依赖 `EventResponse.recording_id` 匹配录制文件。但 Server 的 `EventResponse` schema 缺少 `recording_id` 字段，`ViewResponse` 缺少 `name` 字段，导致前端功能异常。

## What Changes

- **接通录制帧推送**：在 `AIPipeline._run_loop()` 中每帧调用 `replay_task.push_frame()`，将标注帧写入环形缓冲区
- **接通录制生命周期**：在 `start_pipeline()` 中调用 `replay_task.start_buffer()`，在 `stop_pipeline()` 中调用 `replay_task.stop_buffer()`
- **注册 RECORDING 事件订阅者**：在 `vision_task.py` 中订阅 EventBus 的 `RECORDING` 主题，收到事件时调用 `replay_task.alert_triggered()`
- **配置 `SRS_PUBLIC_HOST`**：在 `.env` 中启用并设置 `SRS_PUBLIC_HOST`，使返回给 Web 的 URL 可从浏览器访问
- **`EventResponse` 添加 `recording_id`**：Pydantic schema 补充数据库模型中已有但序列化时被丢弃的字段
- **`ViewResponse` 添加 `name`**：DB 模型和 Schema 补充 View 名称字段，支持 Dashboard 内联重命名

## Capabilities

### New Capabilities

- `recording-frame-feed`: AI 管线每帧将标注帧推入录制环形缓冲区，使录制链路完整
- `recording-event-subscriber`: EventBus RECORDING 主题的订阅者，桥接 AlertEngine → replay_task

### Modified Capabilities

- `clip-replay`: 原 spec 定义了录制回放端点但未约束帧输入来源。本次明确要求 `replay_task.push_frame()` 由 AI 管线主循环调用，`start_buffer`/`stop_buffer` 随管线生命周期启停
- `stream-lifecycle`: 原 spec 约束了 WSS UPDATE_STREAM 命令和推流启停逻辑。本次扩展要求 View 删除时同时清理录制缓冲区和会话
- `situation-event-model`: EventResponse schema 需要新增 `recording_id` 字段，DB 模型已有此列但未暴露
- `monitor-view-model`: ViewResponse schema 需要新增 `name` 字段，MonitorView DB 模型需要新增 `name` 列

## Impact

- **`src/service/vision_task.py`**：`start_pipeline()` 中调用 `replay_task.start_buffer()` + 订阅 RECORDING；`stop_pipeline()` 中调用 `replay_task.stop_buffer()` + 取消订阅
- **`src/service/vision_module/vision_pipeline.py`**：`_run_loop()` 中每帧调用 `replay_task.push_frame()`
- **`src/schema/http/event.py`**：`EventResponse` 添加 `recording_id` 字段
- **`src/schema/http/view_schema.py`**：`ViewResponse` 添加 `name` 字段
- **`src/models/monitor_view.py`**：`MonitorView` 添加 `name` 列
- **`.env` / `.env.example`**：启用 `SRS_PUBLIC_HOST`
- **前端**：无需修改（Web 端已正确消费 `recording_id` 和 `name`）
