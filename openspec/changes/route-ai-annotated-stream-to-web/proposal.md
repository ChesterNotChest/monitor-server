## Why

AI 推理管线（YOLO 检测、人脸识别、行为分析、电子围栏）已在 server 端正常运行，输出的标注视频流成功推送到 SRS，但 Web 前端看到的却是原始合流画面而非 AI 标注画面。根因是两条推流管线目标 SRS RTMP application 不一致——原始合流推到 `/live/`，AI 标注流推到 `/view/`，而 Web 播放 URL 只指向 `/live/`。

## What Changes

- **vision_merger.py**：AI 标注流推流目标从 `/view/{id}` 改为 `/live/{id}`，与原始合流和播放 URL 对齐；ffmpeg 命令加入音频输入（从 SRS 拉取音频 RTMP 流合并）
- **view_task.py**：AI 管线启动成功后，终止原始 ffmpeg 合流子进程，避免两路 ffmpeg 同时推同一 SRS 流发生冲突
- **前端零改动**：播放 URL（`app=live&stream={id}`）不变，Web 端自动看到 AI 标注画面

## Capabilities

### New Capabilities
- `ai-stream-routing`: AI 标注视频流路由到 Web 播放端点，确保 Web 端直播画面包含 YOLO 检测框、人脸标注、行为标签等 AI 标注信息

### Modified Capabilities
- `stream-merge-srs`: AI 标注流推流目标从 `/view/{id}` 改为 `/live/{id}`；原始合流在 AI 管线成功启动后自动让位，改为 AI 管线故障时保底

## Impact

- `src/service/view_task.py` — `create_view()` 合流管控逻辑
- `src/service/vision_module/vision_merger.py` — 推流目标 app + 音频输入
- Web 端：无需改动（播放 URL 不变）
