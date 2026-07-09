# Clip Replay

**Purpose:** 环形缓冲区 + 录制会话的帧格式参数化，确保不同编码格式的帧都能正确录制。

## ADDED Requirements

### Requirement: FrameRingBuffer 格式感知

系统 SHALL 在 `FrameRingBuffer` 上新增 `format` 参数（`"raw_bgr24"` 或 `"jpeg"`），用于告知 `RecordingSession` 上游帧的编码格式。

#### Scenario: 默认 raw BGR24

- **WHEN** `FrameRingBuffer()` 不传 format
- **THEN** `self.format = "raw_bgr24"`

#### Scenario: JPEG 格式

- **WHEN** `FrameRingBuffer(format="jpeg")` 
- **THEN** `self.format = "jpeg"`

### Requirement: RecordingSession 按格式切换 FFmpeg

系统 SHALL 在 `RecordingSession` 创建 FFmpeg 子进程时根据 buffer 的 `format` 切换命令参数。

- `raw_bgr24` SHALL 使用 `-f rawvideo -pix_fmt bgr24 -s WxH -r FPS -i pipe:0 -c:v libx264 -f flv`
- `jpeg` SHALL 使用 `-f image2pipe -c:v mjpeg -i pipe:0 -c:v copy -f flv`

#### Scenario: JPEG 格式录制

- **WHEN** `RecordingSession` 收到 `format="jpeg"` 的 buffer
- **THEN** FFmpeg 以 `-f image2pipe -c:v mjpeg` 接收帧，`-c:v copy` 不重编码

#### Scenario: raw BGR24 格式录制

- **WHEN** `RecordingSession` 收到 `format="raw_bgr24"` 的 buffer
- **THEN** FFmpeg 以 `-f rawvideo -pix_fmt bgr24` 接收帧，`-c:v libx264` 编码

### Requirement: RecordingRepo 原生 INSERT

系统 SHALL 在 `RecordingRepo.create()` 中使用 `db.execute(insert(Recording).values(...))` 代替 `self.model(**kwargs)` → `self.db.add()` → `self.db.commit()`，避免 ORM mapper 在 partial import 场景触发 `FaceRecognitionResult` 解析失败。

#### Scenario: 独立测试中写入 Recording

- **WHEN** 只导入了 `Recording` 模型而未导入全模型树
- **THEN** `RecordingRepo.create()` 正常写入 DB 记录，不触发 `ExceptionDef` mapper 配置
