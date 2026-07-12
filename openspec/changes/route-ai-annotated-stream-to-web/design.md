## Context

当前系统存在两路并行视频推流管线：

1. **原始合流**（`view_task.py` → `subprocess.Popen`）: ffmpeg 拉原始 RTMP 音视频流，stream-copy 合并后推到 SRS `app=live`
2. **AI 标注流**（`vision_merger.py` → `start_stream_merge`）: AI 管线从 pipe:0 读标注帧，编码后推到 SRS `app=view`

Web 播放 URL（`build_play_urls`）指向 `app=live`。AI 标注流推到 `app=view`，不在播放路径上。

## Goals / Non-Goals

**Goals:**
- AI 标注视频流通过现有播放 URL（`app=live`）可达
- AI 管线成功启动后，原始合流自动让位，避免双 ffmpeg 竞争同一 SRS 流
- AI 标注流包含音频

**Non-Goals:**
- 不修改前端代码
- 不修改播放 URL 生成逻辑（`build_play_urls`）
- 不改变 AI 管线的帧处理逻辑（YOLO、标注等）

## Decisions

### Decision 1: 统一 RTMP app 为 `/live/`

**选择**：AI 标注流推流目标从 `/view/{id}` 改为 `/live/{id}`。

**替代方案**：
- 改播放 URL 为 `app=view` — 需改 `build_play_urls` + 前端，改动面更大
- 新建 `ai_webrtc_url` 字段 — 前后端都要改，增加复杂度

**理由**：`/live/` app 已经是 Web 播放的约定路径，AI 标注流直接对齐即可，前端零改动。

### Decision 2: AI 启动后 kill 原始合流

**选择**：`create_view()` 保存原始合流的 `subprocess.Popen` 引用，AI 管线成功启动后调用 `proc.terminate()`。

**替代方案**：
- 保留双流（原始 `/live/` + AI `/view/`）— SRS 同时推两路浪费带宽，且需要双播放 URL
- AI 先停原始再启 — 有短暂画面中断窗口

**理由**：AI 启动后再停原始合流，画面切换无中断（SRS 在旧 publisher 断开后自动切到新 publisher）。

### Decision 3: AI 推流加入音频

**选择**：在 `vision_merger.py` 的 ffmpeg 命令中添加 `-i rtmp://SRS/live/{audio_name}_audio_{id}` 作为第二输入，编码时合并。

**替代方案**：
- 在 SRS 层合并音频 — 需要额外 SRS 配置，增加运维复杂度

**理由**：ffmpeg 原生支持多输入合并，无需改动 SRS 配置。

## Risks / Trade-offs

- **[Risk]** AI 管线崩溃后无画面 → **Mitigation**：`view_task.py` 捕获 AI 管线异常后重新启动原始合流作为保底
- **[Risk]** ffmpeg 音频拉流失败（如音频设备名含中文导致 URL 异常）→ **Mitigation**：音频输入设为可选（`-i` 失败不影响视频推流），允许 video-only 降级
- **[Risk]** 两个 ffmpeg 短暂同时推流（AI 启动和 kill 原始合流之间有时间窗口）→ **Mitigation**：SRS 默认允许新 publisher 替换旧 publisher，窗口期 < 1 秒
