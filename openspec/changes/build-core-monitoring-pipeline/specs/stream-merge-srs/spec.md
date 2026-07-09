# Stream Merge & SRS

**Purpose:** Server 从 SRS 拉取 raw audio+video 流，FFmpeg 合并后推回 SRS，供前端播放。

## ADDED Requirements

### Requirement: 从 SRS 拉取原始流

系统 SHALL 在 `src/network/rtmp/puller.py` 中封装从 SRS 拉取 RTMP 流的能力。拉流地址 SHALL 根据配置构建：`rtmp://{RTMP_HOST}:{RTMP_PORT}/live/{device_name}_{device_type}_{device_id}`，其中 `RTMP_HOST` 在 DEBUG 模式下强制为 `127.0.0.1`。

#### Scenario: 生产环境拉流地址

- **WHEN** `RTMP_DEBUG=false`，`RTMP_HOST=10.126.59.25`，`RTMP_PORT=1935`
- **THEN** audio 拉流地址为 `rtmp://10.126.59.25:1935/live/mic0_audio_1`

#### Scenario: Debug 环境拉流地址

- **WHEN** `RTMP_DEBUG=true`
- **THEN** 拉流地址强制使用 `rtmp://127.0.0.1:{RTMP_PORT}/live/...`

### Requirement: FFmpeg 合并音视频流

系统 SHALL 在 `src/service/view_module/` 中使用 FFmpeg 子进程合并 audio 和 video 流。SHALL 使用 `asyncio.create_subprocess_exec` 启动 FFmpeg 进程，参数 SHALL 为：video input 和 audio input 作为两个 `-i` 源，video 编码 SHALL 使用 `-c:v copy`（不重编码），audio 编码 SHALL 使用 `-c:a aac`，输出格式 SHALL 为 FLV 推送到 SRS。

#### Scenario: 启动 FFmpeg 合并进程

- **WHEN** 创建 View 成功，调用 `start_merge_process(view_id, video_id, audio_id)`
- **THEN** 启动一个 FFmpeg 子进程，合并两路 RTMP 并推送到 `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/view/{view_id}`

#### Scenario: FFmpeg 进程异常退出

- **WHEN** FFmpeg 子进程因流中断或其他原因异常退出
- **THEN** 系统记录错误日志，不自动重启（需通过 View 管理接口手动处理）

### Requirement: 向 SRS 推送合并后的 View 流

系统 SHALL 在 `src/network/rtmp/pusher.py` 中封装向 SRS 推送 RTMP 流的能力。推送地址 SHALL 为 `rtmp://{RTMP_HOST}:{SRS_RTMP_PORT}/view/{view_id}`，其中 `SRS_RTMP_PORT` 默认为 `1935`。

#### Scenario: 推流地址构建

- **WHEN** `SRS_RTMP_PORT=1935`，`RTMP_HOST=10.126.59.25`，`view_id=1`
- **THEN** 推流地址为 `rtmp://10.126.59.25:1935/view/1`

### Requirement: FFmpeg 进程生命周期管理

系统 SHALL 维护一个 `{view_id: subprocess.Popen}` 映射以跟踪活跃的 FFmpeg 进程。删除 View 时 SHALL 向对应进程发送 SIGTERM 信号终止。Server 关闭时 SHALL 终止所有活跃的 FFmpeg 子进程。

#### Scenario: View 删除时终止 FFmpeg

- **WHEN** 删除 View id=1
- **THEN** 向 view_id=1 的 FFmpeg 子进程发送 SIGTERM，等待进程退出，从进程管理映射中移除

#### Scenario: Server 关闭时清理所有子进程

- **WHEN** Server 进程收到关闭信号
- **THEN** 遍历所有活跃的 FFmpeg 子进程，逐一发送 SIGTERM

### Requirement: SRS 播放地址返回

系统 SHALL 在 View 详情中返回 SRS 播放地址。播放地址 SHALL 格式为 `http://{SRS_HOST}:{SRS_HTTP_PORT}/live/view_{view_id}.flv`（HTTP-FLV），以及 `webrtc://{SRS_HOST}:{SRS_HTTP_PORT}/live/view_{view_id}`（WebRTC）。

#### Scenario: 获取 View 的播放地址

- **WHEN** `SRS_HOST=10.126.59.25`，`SRS_HTTP_PORT=8082`，`view_id=1`
- **THEN** 返回 `flv_url: "http://10.126.59.25:8082/live/view_1.flv"` 和 `webrtc_url: "webrtc://10.126.59.25:8082/live/view_1"`
