## ADDED Requirements

### Requirement: AI 管线每帧推送标注帧到录制缓冲区

系统 SHALL 在 AI 管线主循环（`AIPipeline._run_loop()`）中，每帧标注完成后调用 `replay_task.push_frame(view_id, frame.tobytes())`，将已标注的 BGR24 帧字节写入该 View 的录制环形缓冲区。

#### Scenario: 管线运行中帧持续写入缓冲区

- **WHEN** AI 管线正在运行（`_run_loop` 主循环）且合并器已启动
- **THEN** 每帧通过 `push_frame()` 写入环形缓冲区和活跃的 RecordingSession（若存在）

#### Scenario: 缓冲区未初始化时不报错

- **WHEN** `push_frame(view_id, frame_bytes)` 被调用但该 `view_id` 尚未调用 `start_buffer()`
- **THEN** 函数静默返回，不抛出异常

### Requirement: 录制缓冲区随管线生命周期启停

系统 SHALL 在 View 的 AI 管线启动时调用 `replay_task.start_buffer(view_id)` 初始化环形缓冲区，在管线停止时调用 `replay_task.stop_buffer(view_id, db)` 清理缓冲区和活跃录制会话。

#### Scenario: 管线启动时初始化缓冲区

- **WHEN** `start_pipeline(view_id, ...)` 被调用
- **THEN** 系统调用 `replay_task.start_buffer(view_id)` 创建该 View 的环形缓冲区

#### Scenario: 管线停止时清理缓冲区

- **WHEN** `stop_pipeline(view_id)` 被调用
- **THEN** 系统调用 `replay_task.stop_buffer(view_id, db)` 停止活跃录制会话并清空缓冲区
