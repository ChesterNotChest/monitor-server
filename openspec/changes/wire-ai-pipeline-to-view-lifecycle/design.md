## Context

三个断点，调用顺序固定：

```
create_view
  → start_pipeline(view_id, video_id, video.name, audio_id, audio.name)
      → AIPipeline.start
      → register_video_ai_hooks(pipeline, view_id)    ← NEW
      → AlertEngine.start
      → YamnetRunner.run (if audio_id)
          → _run_loop
              → YOLO
              → frame hooks (Part B)
              → draw_detections
              → draw_part_b_overlay(ctx.tracks, ...)   ← NEW
```

## Decisions

### Decision 1: `create_view` 是唯一调用点

`start_pipeline` 只在 View 创建时调用。删除 View 时已有的 `stop_pipeline` 调用不变。

**Rationale**: View 是 Node 推流和 Server 拉流的汇聚点。View 创建 = 推流开始 + 管线启动。

### Decision 2: `register_video_ai_hooks` 在 `start_pipeline` 中调用

不放在 `AIPipeline.start()` 内部——保持 Part A 独立于 Part B。

**Rationale**: `register_video_ai_hooks` 依赖 `VideoAIProcessor`，它创建 ByteTracker + FaceRecognizer + FenceEngine + SlowFastRunner。这些模块都是可选的（Part B 可能未合入），放在 `start_pipeline` 中方便 try/except 容错。

### Decision 3: `draw_part_b_overlay` 参数从 `ctx.tracks` 推导

`_run_loop` 调用 `draw_part_b_overlay` 时传入 `ctx.tracks`，其余 `face_labels`/`action_labels`/`fence_labels`/`fence_polygons` 暂传空。各模块通过 `_frame_hooks` 产出数据后，后续可追加到 `FrameContext` 并从 hooks 中读取再传入。

**Rationale**: `ctx.tracks` 已由 ByteTracker 填充至 `FrameContext`。face/action/fence 的标签缓存在各模块内部，需要在 `FrameContext` 上开字段或通过 EventBus 回调写入——这留给各模块负责人后续优化。当前先打通 ByteTrack ID 的显示。
