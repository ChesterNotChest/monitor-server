## 1. AI 推流目标对齐

- [x] 1.1 `vision_merger.py` `_build_push_url()` — RTMP app 从 `/view/` 改为 `/live/`，与 `build_push_url()` 和 `build_play_urls()` 对齐
- [x] 1.2 `vision_merger.py` `start_stream_merge()` — ffmpeg 命令添加第二个输入 `-i rtmp://SRS/live/{audio_name}_audio_{id}`，音频流合并进输出 FLV

## 2. 原始合流让位逻辑

- [x] 2.1 `view_task.py` `create_view()` — 原始合流 `subprocess.Popen` 返回值（进程对象）保存在局部变量中
- [x] 2.2 `view_task.py` `create_view()` — AI 管线成功启动后，调用 `proc.terminate()` 终止原始合流 FFmpeg 进程
- [x] 2.3 `view_task.py` `create_view()` — AI 管线 import 失败时，保留原始合流并记录 warning（已有逻辑，确认无回归）

## 3. AI 异常降级保底

- [x] 3.1 `view_task.py` `create_view()` — 通过 `proc.poll() is None` 检查进程存活后再 terminate，异常退出已有隐式保护
- [x] 3.2 确认 `delete_view()` 中 `stop_merge` + `stop_pipeline` 停止顺序：先停原始合流，AI 标注流最后停，顺序正确

## 4. 端到端验证

- [ ] 4.1 创建 View → SRS 确认 `/live/{view_id}` 流存在且包含 H264 视频
- [ ] 4.2 浏览器进入 LiveMonitor → 视频画面包含 YOLO 检测框等 AI 标注叠加
- [ ] 4.3 删除 View → 确认 SRS 上 `/live/{view_id}` 流被正确清理
