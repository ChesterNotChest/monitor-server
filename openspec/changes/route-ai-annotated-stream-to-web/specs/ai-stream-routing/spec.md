# AI Stream Routing

## Purpose

AI 标注视频流 SHALL 路由到 Web 端播放端点，确保浏览器看到的直播画面包含
YOLO 检测框、人脸标注、行为标签、电子围栏标记等 AI 推理叠加信息。

## ADDED Requirements

### Requirement: AI-annotated stream targets Web playback app

AI 管线 SHALL 将标注后的视频流推送到与 Web 播放 URL 相同的 SRS RTMP application
（`/live/`），确保 Web 端无需任何改动即可看到标注画面。

#### Scenario: AI pipeline push matches play URL

- **WHEN** Server 启动 AI 管线处理 view_id=1
- **THEN** AI 管线 FFmpeg 推流到 `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/live/1`
- **AND** Web 播放 URL `app=live&stream=1` 展示的画面包含 AI 标注叠加

### Requirement: AI-annotated stream includes audio

AI 管线推流 SHALL 包含音频轨道。Server SHALL 从 SRS 拉取原始音频 RTMP 流，
与标注后的视频帧合并为一路带音频的 FLV/RTMP 输出。

#### Scenario: AI stream with audio

- **WHEN** AI 管线为 view_id=1 启动标注推流
- **THEN** FFmpeg 命令包含视频输入（pipe:0，标注帧）和音频输入（`rtmp://SRS/live/{audio_name}_audio_{id}`）
- **AND** 输出 FLV 同时包含 H264 视频和 AAC 音频

### Requirement: Raw merge yields to AI pipeline

当 AI 管线成功启动后，Server SHALL 终止原始合流 FFmpeg 子进程。
当 AI 管线不可用或异常退出时，原始合流 SHALL 作为保底恢复推流。

#### Scenario: AI takes over from raw merge

- **WHEN** `create_view()` 成功启动 AI 管线
- **THEN** Server 终止之前启动的原始合流 FFmpeg 进程
- **AND** SRS 上 `/live/{view_id}` 流由 AI 管线独占推送

#### Scenario: AI unavailable, raw merge stays

- **WHEN** AI 依赖未安装导致 import 失败
- **THEN** 原始合流 FFmpeg 继续保持推流
- **AND** Web 端可看到原始无标注画面作为降级体验
