## 1. AI 管线主循环接入帧推送

- [ ] 修改 `src/service/vision_module/vision_pipeline.py` 的 `_run_loop()`
  - 在 `push_frame(self._merge_proc, annotated)` 之后，调用 `replay_task.push_frame(view_id, annotated_frame_bytes)`
  - 需要将 `annotated` numpy 数组转为 bytes：`annotated.tobytes()`
  - 导入 `from src.service import replay_task`

## 2. 管线启动时初始化录制缓冲区

- [ ] 修改 `src/service/vision_task.py` 的 `start_pipeline()`
  - 在创建 AIPipeline 之后（AlertEngine 之前或之后），调用 `replay_task.start_buffer(view_id)`
  - 导入 `from src.service import replay_task`

## 3. 管线停止时清理录制缓冲区

- [ ] 修改 `src/service/vision_task.py` 的 `stop_pipeline()`
  - 在停止 AlertEngine 之后、AIPipeline 之前，调用 `replay_task.stop_buffer(view_id, db)`
  - `stop_buffer` 需要一个 SQLAlchemy Session：使用 `SessionLocal()` 创建独立 session
  - 确保 session 在 finally 中关闭

## 4. 注册 EventBus RECORDING 订阅者

- [ ] 在 `src/service/vision_task.py` 中添加 RECORDING 事件的异步订阅者回调
  - 回调调用 `replay_task.alert_triggered(view_id, db)`，使用独立 `SessionLocal()`
  - 使用模块级标志 `_recording_subscribed` 确保全局只注册一次
  - 在 `start_pipeline()` 中调用 `event_bus.subscribe(RECORDING, _on_recording)`
  - 在 `stop_pipeline()` 中，若所有管线已停止，调用 `event_bus.unsubscribe(RECORDING, _on_recording)`

## 5. 配置 SRS_PUBLIC_HOST

- [ ] 在 `monitor-server/.env` 中取消 `SRS_PUBLIC_HOST` 的注释并设置实际 IP
- [ ] 在 `monitor-server/.env.example` 中添加注释说明不同环境应如何配置

## 6. EventResponse 添加 recording_id 字段

- [ ] 修改 `src/schema/http/event.py` 的 `EventResponse`
  - 添加 `recording_id: int | None = Field(None, description="关联录制 ID")`
  - DB 模型 `SituationEvent` 已有此列，`from_attributes=True` 会自动映射

## 7. ViewResponse 添加 name 字段

- [ ] 修改 `src/models/monitor_view.py` 的 `MonitorView`
  - 添加 `name: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)`
- [ ] 修改 `src/schema/http/view_schema.py` 的 `ViewResponse`
  - 添加 `name: str | None = Field(None, description="视图名称")`
- [ ] 修改 `src/service/view_task.py` 中三处构造 `ViewResponse` 的代码（`create_view`、`get_view`、`list_views`）
  - 每个 `ViewResponse(...)` 调用中添加 `name=view.name`

## 8. 端到端验证

- [ ] 启动 SRS + Server + Node 三进程
- [ ] 创建 View → 确认 `flv_url` 和 `webrtc_url` 使用 `SRS_PUBLIC_HOST` 而非 `127.0.0.1`
- [ ] 确认 `ViewResponse.name` 字段存在
- [ ] 确认 `EventResponse.recording_id` 字段存在
- [ ] 触发告警 → 确认录制文件生成且非空
- [ ] EventReplay 页面能通过 `recording_id` 匹配并正常播放回放
- [ ] LiveMonitor 页面能通过 `webrtc_url` + WHEP 正常播放直播
