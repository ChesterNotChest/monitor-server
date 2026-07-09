## Why

Smoke test 暴露两个 bug：(1) `FrameRingBuffer` 存 `bytes` 无格式信息，`RecordingSession` 硬编码 `-f rawvideo -pix_fmt bgr24`，上游推 JPEG 帧时 FFmpeg 按 raw BGR24 解析 → 录制产物只有 0.1s。(2) `RecordingRepo.create()` 触发 `ExceptionDef` mapper 配置时 `FaceRecognitionResult` 字符串引用无法解析（partial import 场景）。

## What Changes

- **FrameRingBuffer** 新增 `format` 参数（`raw_bgr24` / `jpeg`），透传到 RecordingSession
- **RecordingSession** 根据 `format` 切换 FFmpeg `-f rawvideo` 或 `-f image2pipe -c:v copy`
- **RecordingRepo** 改为直接写 SQL INSERT，绕过 ORM mapper 配置（消除 partial import 崩溃）

## Capabilities

### Modified Capabilities

- `clip-replay`: FrameRingBuffer + RecordingSession 帧格式参数化；RecordingRepo 改用原生 SQL

## Impact

- `src/service/replay_module/ring_buffer.py` — 加 `format` 字段
- `src/service/replay_module/recorder.py` — 按 `format` 切换 FFmpeg 参数
- `src/repository/recording_repo.py` — `create()` 改用 `db.execute(insert(Recording).values(...))`
