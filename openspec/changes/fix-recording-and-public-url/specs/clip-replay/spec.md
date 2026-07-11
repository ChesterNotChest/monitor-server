## ADDED Requirements

### Requirement: 录制链路输入来源明确化

`replay_task.push_frame()` SHALL 由 AI 管线主循环（`AIPipeline._run_loop()`）在每帧标注完成后调用。`replay_task.start_buffer()` SHALL 在 `start_pipeline()` 中调用。`replay_task.stop_buffer()` SHALL 在 `stop_pipeline()` 中调用。`replay_task.alert_triggered()` SHALL 由 EventBus `RECORDING` 订阅者调用。

#### Scenario: push_frame 调用链完整

- **WHEN** AI 管线主循环在标注帧后执行
- **THEN** `replay_task.push_frame(view_id, annotated_frame.tobytes())` 被调用

#### Scenario: start_buffer 调用链完整

- **WHEN** `view_task.create_view()` 触发 `start_pipeline()`
- **THEN** `replay_task.start_buffer(view_id)` 在管线启动流程中被调用

#### Scenario: stop_buffer 调用链完整

- **WHEN** `view_task.delete_view()` 触发 `stop_pipeline()`
- **THEN** `replay_task.stop_buffer(view_id, db)` 在管线停止流程中被调用
