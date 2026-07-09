# Device Discovery

**Purpose:** Node 连接时 Server 回传已有设备映射，Node 本地维护 (name → id) 映射。新设备通过 DEVICE_CHANGED 事件补充上报。

## ADDED Requirements

### Requirement: 连接握手时推送已有设备映射

系统 SHALL 在 Node WSS 连接认证成功后，查询该 Node 下已有的所有 VideoDevice 和 AudioDevice，将列表随 `session_token` 一起回传给 Node。Node 收到后 SHALL 在本地维护 `(device_name → device_id)` 映射表，供后续 `UPDATE_STREAM` 命令中根据 `device_id` 反查物理设备名称。

#### Scenario: Server 回传已有设备

- **WHEN** Node 认证成功，DB 中该 Node 已有 `cam0 (video_id=1)` 和 `mic0 (audio_id=2)`
- **THEN** Server 返回 `{session_token, videos: [{id: 1, name: "cam0"}], audios: [{id: 2, name: "mic0"}]}`
- **AND** Node 本地建立映射 `{"cam0" → 1, "mic0" → 2}`

#### Scenario: Node 无已有设备（首次连接）

- **WHEN** Node 认证成功，DB 中该 Node 下无任何设备
- **THEN** Server 返回 `{session_token, videos: [], audios: []}`

### Requirement: 按 Node 查询设备列表

系统 SHALL 提供 API 接口，允许前端按 Node 查询该节点下的视频设备和音频设备列表。

#### Scenario: 查询指定 Node 的视频设备

- **WHEN** 前端请求 `GET /api/v1/nodes/{node_id}/videos`
- **THEN** 返回该 Node 下所有 VideoDevice，每个包含 `id`、`name`、`streaming` 状态

#### Scenario: 查询指定 Node 的音频设备

- **WHEN** 前端请求 `GET /api/v1/nodes/{node_id}/audios`
- **THEN** 返回该 Node 下所有 AudioDevice，每个包含 `id`、`name`、`streaming` 状态

### Requirement: 设备唯一性约束

同一个 Node 下的设备名称 SHALL 唯一。Server 的连接握手响应中 SHALL 不返回重复设备。

#### Scenario: 连接握手不返回重复设备

- **WHEN** Server 查询该 Node 下的设备列表
- **THEN** 返回的列表中每个 (node_id, name) 组合只出现一次
