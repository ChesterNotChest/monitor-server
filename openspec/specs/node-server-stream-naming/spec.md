# Node-Server Stream Naming

**Purpose:** 对 Node → Server 原始设备流的 RTMP 推拉流命名进行强制约束，保证两侧一致。

## ADDED Requirements

### Requirement: 原始流命名格式
系统 SHALL 使用 `rtmp://{host}:{port}/live/{device_name}_{device_type}_{device_id}` 作为所有 Node → Server 原始设备流的唯一合法命名格式。

- `device_name`：设备名称，空格替换为下划线
- `device_type`：设备类型（`video` 或 `audio`）
- `device_id`：Server 侧 VideoDevice / AudioDevice 的数据库 ID

#### Scenario: Node 推视频流
- **WHEN** Node 启动视频设备 "Webcam Camera"（Server device_id=3）
- **THEN** 推流到 `rtmp://{host}:{port}/live/Webcam_Camera_video_3`

#### Scenario: Node 推音频流
- **WHEN** Node 启动音频设备 "Microphone Array"（Server device_id=7）
- **THEN** 推流到 `rtmp://{host}:{port}/live/Microphone_Array_audio_7`

#### Scenario: Server AI 管线拉视频流
- **WHEN** Server FrameReader 拉取 video_id=3、name="Webcam Camera" 的原始流
- **THEN** 从 `rtmp://{host}:{port}/live/Webcam_Camera_video_3` 拉流

#### Scenario: Server 音频模块拉音频流
- **WHEN** Server YamnetRunner 拉取 audio_id=7、name="Microphone Array" 的原始流
- **THEN** 从 `rtmp://{host}:{port}/live/Microphone_Array_audio_7` 拉流

### Requirement: Server 侧统一使用 build_pull_url
Server 内部 SHALL 统一通过 `src.network.rtmp.puller.build_pull_url(device_name, device_type, device_id)` 构造原始流拉流地址。禁止在 vision_module、audio_module、view_module 中硬编码 URL 格式。

#### Scenario: 违反格式被拒绝
- **WHEN** 代码审查发现 `rtmp://.../live/video_{id}` 或 `rtmp://.../live/audio_{id}` 等硬编码格式
- **THEN** 视为不合规，必须改用 `build_pull_url()`

### Requirement: 二次推流不受本规范约束
Server 向 Web 端推送的标注合并流（`/view/{view_id}`）使用独立的命名空间，由 `build_push_url` 管理，不受本规范约束。
