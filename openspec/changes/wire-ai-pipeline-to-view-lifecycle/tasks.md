## 1. view_task.py — View 创建时启动 AI 管线

- [x] 1.1 `create_view` 中 import `start_pipeline` from `vision_task`
- [x] 1.2 在 View 创建成功且 `video is not None` 后，调用 `await start_pipeline(view.id, video_id, video.name, audio_id, audio.name)`

## 2. vision_task.py — 管线启动时注册 Part B

- [x] 2.1 `start_pipeline` 中，`AIPipeline.start` 成功后，调用 `register_video_ai_hooks(pipeline, view_id)`
- [x] 2.2 用 try/except 包裹，失败时 logger.warning 不阻塞管线启动

## 3. vision_pipeline.py — 标注层追加 Part B 内容

- [x] 3.1 `_run_loop` 中 `draw_detections` 之后，调用 `draw_part_b_overlay(frame, ctx.tracks)`
- [x] 3.2 用 `ctx.tracks if ctx.tracks else []` 兜底 None 情况

## 4. 验证

- [x] 4.1 核心测试回归：`pytest src/tests/api/ src/tests/e2e/ src/tests/service/test_stream_pipeline.py -q` 全通过
- [ ] 4.2 模式二全链路：VLC 能看到 YOLO 框 + ByteTrack ID
