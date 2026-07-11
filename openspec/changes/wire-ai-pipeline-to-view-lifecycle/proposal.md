## Why

Part A (YOLO + 标注 + 合流)、Part B (ByteTrack + Face + Fence + SlowFast)、Part C (AlertEngine + YamnetRunner) 三个模块各自完整，但从未被串入 View 创建的生命周期。`create_view` 只发送 WSS UPDATE_STREAM 命令启动 Node 推流，不启动 Server 的 AI 管线。结果是 :1936 只能看到原始合并画面，没有任何 AI 标注。三个断点、8 行胶水代码。

## What Changes

- `view_task.py`: `create_view` 中调用 `vision_task.start_pipeline`，传入 `video.name`
- `vision_task.py`: `start_pipeline` 中调用 `register_video_ai_hooks`，注册 Part B 模块
- `vision_pipeline.py`: `_run_loop` 中调用 `draw_part_b_overlay`，叠加 Part B 标注

## Capabilities

### New Capabilities
<!-- None — wiring only, no new capability. -->

### Modified Capabilities
<!-- None — no spec-level behavior change. -->

## Impact

- **3 文件修改**: `view_task.py`（+2 行）、`vision_task.py`（+2 行）、`vision_pipeline.py`（+4 行）
- **零新增文件**: 所有模块已存在
- **向后兼容**: `start_pipeline` 已处理 audio_id=None 的情况；`draw_part_b_overlay` 所有参数可选
