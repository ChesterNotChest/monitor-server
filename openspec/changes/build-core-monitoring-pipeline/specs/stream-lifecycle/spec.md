# Stream Lifecycle

**Purpose:** 基于 View 引用计数的推流启停逻辑，通过 WSS 向 Node 发送 UPDATE_STREAM 命令。

## ADDED Requirements

### Requirement: 推流引用计数查询

系统 SHALL 在创建或删除 View 时实时查询 `monitor_views` 表，计算指定 audio 设备或 video 设备的当前引用计数。引用计数定义为 `SELECT COUNT(*) FROM monitor_views WHERE video_id = ?` 或 `audio_id = ?`。

#### Scenario: 查询 video 设备引用计数

- **WHEN** 调用 `get_video_ref_count(video_id)`
- **THEN** 返回当前使用该 video 的 View 数量

#### Scenario: 查询 audio 设备引用计数

- **WHEN** 调用 `get_audio_ref_count(audio_id)`
- **THEN** 返回当前使用该 audio 的 View 数量

### Requirement: 推流启动判断

创建 View 时，系统 SHALL 对 audio 和 video 分别判断：若该设备在被新 View 引用前的引用计数为 0，则 SHALL 通过 WSS 向设备所属 Node 发送 `UPDATE_STREAM` 命令（`enable=true`）。若引用计数大于 0，则 SHALL 不发送命令，并在 API 响应中标记该设备为"已被其他 View 使用"。

#### Scenario: 首个 View 触发推流启动

- **WHEN** 创建 View 引用 video_id=1，且创建前 video_id=1 的引用计数为 0
- **THEN** 向 video 所属 Node 发送 `UPDATE_STREAM {device_type: "video", device_id: 1, enable: true}`（Node 通过连接握手时建立的映射表反查 `device_id → device_name`）

#### Scenario: 非首个 View 不触发推流

- **WHEN** 创建 View 引用 audio_id=2，且创建前 audio_id=2 的引用计数为 1（已被另一个 View 使用）
- **THEN** 不发送 `UPDATE_STREAM`，API 响应中包含 `warnings: ["audio_id=2 已被 1 个 View 使用"]`

### Requirement: 推流停止判断

删除 View 时，系统 SHALL 在删除 View 记录后对 audio 和 video 分别判断：若该设备在删除后的引用计数为 0，则 SHALL 通过 WSS 向设备所属 Node 发送 `UPDATE_STREAM` 命令（`enable=false`）。若引用计数仍大于 0，则 SHALL 不发送命令。

#### Scenario: 最后一个 View 删除触发推流停止

- **WHEN** 删除 View 后 video_id=1 的引用计数降为 0
- **THEN** 向 video 所属 Node 发送 `UPDATE_STREAM {device_type: "video", device_id: 1, enable: false}`（Node 通过连接握手时建立的映射表反查 `device_id → device_name`）

#### Scenario: 仍有其他 View 引用时停止删除不触发推流停止

- **WHEN** 删除 View 后 audio_id=2 的引用计数为 1（仍有一个 View 使用）
- **THEN** 不发送 `UPDATE_STREAM`

### Requirement: VideoDevice/AudioDevice streaming 状态同步

系统 SHALL 在发送 `UPDATE_STREAM` 命令并收到 Node 成功响应后，更新 `video_devices` 或 `audio_devices` 表中对应记录的 `streaming` 字段。

#### Scenario: 推流启动成功后更新状态

- **WHEN** Node 响应 `UPDATE_STREAM enable=true` 成功
- **THEN** 更新对应设备记录的 `streaming=true`

#### Scenario: 推流停止成功后更新状态

- **WHEN** Node 响应 `UPDATE_STREAM enable=false` 成功
- **THEN** 更新对应设备记录的 `streaming=false`

### Requirement: Node 断连时设备状态级联清理

系统 SHALL 在 Node 的 WSS 连接断开时，将该 Node 下所有 `streaming=true` 的设备状态更新为 `streaming=false`，防止脏数据。WebSocket 断开回调中 SHALL 执行此清理逻辑。

#### Scenario: Node 异常断连

- **WHEN** Node 的 WSS 连接异常断开，且该 Node 下有 3 个 VideoDevice 的 `streaming=true`
- **THEN** 系统将这三个设备的 `streaming` 全部更新为 `false`

#### Scenario: Node 正常断开

- **WHEN** Node 主动关闭 WSS 连接
- **THEN** 系统同样执行设备状态级联清理，将该 Node 下所有设备的 `streaming` 设为 `false`
