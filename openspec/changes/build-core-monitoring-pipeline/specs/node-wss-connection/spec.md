# Node WSS Connection

**Purpose:** Node 通过 WSS 连接 Server，Server 维护连接注册表，支持双向命令通信。

## ADDED Requirements

### Requirement: Node WSS 连接建立与认证

系统 SHALL 在 `src/network/wss/node_handler.py` 中提供 WebSocket 端点，接收 Node 的连接请求。Node 连接后 SHALL 在首条消息中发送 `token` 进行认证。认证通过后，Server SHALL 查询该 Node 下已有的所有 VideoDevice 和 AudioDevice，生成 `session_token`，将 `(device_name → device_id)` 映射随 `session_token` 一起回传给 Node。Server SHALL 将 WebSocket 连接对象写入 ConnectionRegistry，并将 Node 表中 `is_connected` 设为 true、`last_seen` 更新为当前时间。

#### Scenario: Node 成功连接并认证

- **WHEN** Node 向 WSS 端点发送连接请求，并在首条消息中提供有效 `token`
- **THEN** Server 验证 token，查询该 Node 下已有的 device 列表，生成 session_token，返回 `{session_token, videos: [{id, name}, ...], audios: [{id, name}, ...]}`，将连接写入 ConnectionRegistry，更新 Node 表 `is_connected=true`、`last_seen=NOW()`

#### Scenario: Node 连接时 token 无效

- **WHEN** Node 向 WSS 端点发送连接请求，提供无效或未注册的 `token`
- **THEN** Server 关闭 WebSocket 连接，返回错误信息，不写入 ConnectionRegistry

#### Scenario: 同一 Node 重复连接

- **WHEN** 已连接的 Node 用相同 token 再次建立 WSS 连接
- **THEN** Server 关闭旧连接，将新连接写入 ConnectionRegistry

#### Scenario: Node 首次连接（无已有设备）

- **WHEN** Node 首次连接认证通过，但 DB 中该 Node 下无任何设备记录
- **THEN** Server 返回空列表 `{session_token, videos: [], audios: []}`

### Requirement: ConnectionRegistry 内存注册表

系统 SHALL 在 `network/wss/` 中维护一个内存中的 ConnectionRegistry，存储 `{node_id: WebSocket}` 映射。连接建立时写入，连接断开时移除。外部模块通过 registry 获取指定 Node 的 WebSocket 对象以发送命令。

#### Scenario: 获取在线 Node 的连接对象

- **WHEN** 业务模块调用 `ConnectionRegistry.get(node_id)`
- **THEN** 若 Node 在线，返回其 WebSocket 对象；若离线，返回 None

#### Scenario: Node 断开连接时清理

- **WHEN** Node 的 WebSocket 连接断开（正常关闭或异常中断）
- **THEN** ConnectionRegistry 移除该 Node 的映射，Node 表更新 `is_connected=false`、`last_seen=NOW()`，级联将该 Node 下所有设备的 `streaming` 设为 `false`

### Requirement: 向 Node 发送命令

系统 SHALL 提供 `send_command(node_id, command_payload)` 方法，从 ConnectionRegistry 获取 Node 的 WebSocket 连接，发送 JSON 格式的命令并等待响应。命令格式由 `src/schema/wss/node_commands.py` 中的 Pydantic 模型定义。`device_id` 泛指 video_id 或 audio_id——Node 侧通过连接握手时建立的 `(name → id)` 映射反查物理设备名称。

#### Scenario: 成功发送命令并收到响应

- **WHEN** 调用 `send_command(node_id, UpdateStreamRequest(device_type="video", device_id=1, enable=True))`
- **THEN** 服务器通过 WSS 发送 JSON 命令，等待 Node 响应，返回解析后的响应对象

#### Scenario: 目标 Node 离线

- **WHEN** 调用 `send_command(node_id, ...)` 但 Node 不在 ConnectionRegistry 中
- **THEN** 抛出 NodeOfflineError 异常

### Requirement: Node 在线状态查询

系统 SHALL 通过 Node 表的 `is_connected` 和 `last_seen` 字段提供 Node 在线状态。API 接口返回 Node 列表时 SHALL 包含在线状态信息。

#### Scenario: 查询所有 Node 及其在线状态

- **WHEN** 前端请求 `GET /api/v1/nodes`
- **THEN** 返回 Node 列表，每个 Node 包含 `id`、`token`、`is_connected`、`last_seen` 和 `created_at`

### Requirement: Inbound Node messages are classified before command response handling

Server SHALL keep a single receive loop per authenticated Node WebSocket
connection. Each inbound JSON message SHALL be classified by message shape
before it can satisfy a pending command response.

#### Scenario: Heartbeat is received while a command is pending

- **WHEN** Server has sent `UPDATE_STREAM` and is waiting for the command response
- **AND** Node sends `{"type": "heartbeat"}` before the command response
- **THEN** Server updates the Node connection heartbeat state
- **AND** Server SHALL NOT validate the heartbeat as `UpdateStreamResponse`
- **AND** Server continues waiting for the command response

#### Scenario: Typed update stream response is received

- **WHEN** Node sends `{"type": "update_stream_response", "success": true, "message": "ok"}`
- **THEN** Server routes the message to the pending `send_command()` waiter
- **AND** Server returns an `UpdateStreamResponse` to the caller

#### Scenario: Legacy command response is received

- **WHEN** Node sends `{"success": true, "message": "ok"}` without a `type` field
- **THEN** Server treats the payload as a command response for backward compatibility
