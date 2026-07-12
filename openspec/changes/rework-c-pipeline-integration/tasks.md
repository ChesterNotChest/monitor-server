## 1. Part C 启停 — vision_task.py

- [x] 1.1 `start_pipeline()` 中 AIPipeline 启动成功后创建并启动 AlertEngine；有 audio_id 时创建 YamnetRunner 并用 `asyncio.create_task` 启动
- [x] 1.2 `stop_pipeline()` 中先停 YamnetRunner → AlertEngine → 再 AIPipeline
- [x] 1.3 `stop_all()` 确认覆盖所有模块清理（遍历 `list(_active_pipelines.keys())`）

## 2. 触发点 — View 创建时启动管线

- [x] 2.1 `view_task.py` 的 `create_view()` 末尾调用 `vision_task.start_pipeline(view_id, video_id, video_name, audio_id, audio_name)`

## 3. 清理旧测试文件

- [x] 3.1 删除 `src/tests/test_alert_engine_unit.py`（已不存在）
- [x] 3.2 删除 `src/tests/test_fence_event_types.py`（已不存在）

## 4. §五 一步到位标注方案 — 单遍绘制

**目标**：去掉 `draw_part_b_overlay` 的第二遍绘制，改为在 YOLO detection 上直接附加 track_id / face / action / fence 信息，`draw_detections` 一次画完。

- [x] 4.1 `Detection` 新增 `label_suffix: str | None = None` 字段（`vision_yolo/detector.py`）
- [x] 4.2 `draw_detections` 支持 `label_suffix`——拼接在实体标签后，如 `"Person ID 3 Face: 张三"`（`vision_annotation.py`）
- [x] 4.3 `_run_loop` 中 `draw_detections` 调用前，用 `ctx.tracks` 的 track_id 匹配 detection（IoU 或 bbox 最近邻），写入 `det.label_suffix`；同时从 `_face_labels`（EventBus FACE topic 缓存）取 face label 并入 suffix
- [x] 4.4 删除 `_run_loop` 中对 `draw_part_b_overlay` 的调用（`vision_pipeline.py:179`）

**效果**：省去 `draw_part_b_overlay` 的 `frame.copy()`（~1ms/帧），Bug #1（返回值丢弃）和 Bug #2（face_labels 未传入）随代码删除而消失。

## 5. 编码器三级回退 — vision_merger.py

**目标**：当前写死 `libx264`。改为自动检测最优可用编码器。

- [x] 5.1 新增 `_detect_encoder()` 函数：`torch.cuda.is_available()` → 探测 `h264_nvenc`；Windows 平台探测 `h264_mf`；兜底 `libx264`
- [x] 5.2 探测方式：`subprocess.run([ffmpeg, "-encoders"], capture_output=True)` 检查输出中是否含编码器名
- [x] 5.3 `start_stream_merge` 中 `_detect_encoder()` 替代硬编码 `libx264`；NVENC 参数：`-c:v h264_nvenc -preset p1 -tune ll -b:v 2M -rc vbr`
- [x] 5.4 logger.info 输出实际选用的编码器，便于排查

**注意**：不修改 Node 侧编码器逻辑（任务 1 范围），只改 Server 侧 AI 标注合流的编码器。

## 6. Push 异步化（可选，NVENC 启用后评估）

**目标**：`drain()` 的编码延迟不再反压主循环。

- [x] 6.1 新增 `asyncio.Queue(maxsize=2)` 帧缓冲队列
- [x] 6.2 后台 drain task：从队列取帧 → `write()` + `drain()`
- [x] 6.3 主循环：`queue.put_nowait(frame)` ——队列满则跳过（自然丢帧不阻塞）
- [x] 6.4 NVENC 启用后评估 drain 延迟：若 <3ms 则此优化非必需，可关闭（异步基础设施已就位，待 NVENC 确认后评估）

## 7. 验证

- [x] 7.1 全量 pytest 零失败（排除已知 cv2/numpy 依赖问题）— 244 passed, 3 pre-existing failures, 1 skipped, 2 TF errors。无新增回归。
- [ ] 7.2 模式二全链路：VLC 播放 `rtmp://127.0.0.1:1936/view/{id}`，标注框显示 `"Person ID N"` 格式（单遍绘制生效）
- [ ] 7.3 日志验证编码器选择：启动时出现 `Using encoder: h264_nvenc` 或 `h264_mf` 或 `libx264`
- [ ] 7.4 View 启停循环 3 次，asyncio task 无泄漏
