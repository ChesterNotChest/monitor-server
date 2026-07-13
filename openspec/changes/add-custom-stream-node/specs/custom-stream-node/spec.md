# Custom Stream Node

**Purpose:** 提供虚拟 Node 承载外部 RTMP 流设备，支持注册、验证、View 创建全流程。

## ADDED Requirements

### Requirement: SEED 虚拟 Node
系统 SHALL 在 `seed_admin()` 中预置一个常驻虚拟 Node，`name="virtual"`, `is_connected=False`。该 Node 不接受 WSS 连接。

#### Scenario: 首次启动创建虚拟 Node
- **WHEN** 系统首次启动且 nodes 表中无 "virtual" 节点
- **THEN** 系统创建 `Node(name="virtual", is_connected=False)`

### Requirement: 向虚拟 Node 注册 RTMP 设备
系统 SHALL 提供 `POST /api/v1/nodes/{node_id}/devices/` 端点，接受 `device_type` ("video"/"audio")、`name`、`stream_url`。创建前用 ffprobe 验证流可达（超时 5s），不可达返回 400。

#### Scenario: 成功注册视频流
- **WHEN** 用户 POST `{device_type:"video", name:"IPC-大门", stream_url:"rtmp://10.0.0.5/live/main"}`
- **THEN** 系统插入 VideoDevice(node_id, name, stream_url)，返回 201

#### Scenario: RTMP 不可达
- **WHEN** ffprobe 超时
- **THEN** 系统返回 400 "流不可达"

### Requirement: FrameReader 使用 stream_url
系统 SHALL 在 VideoDevice 新增 `stream_url` 字段。FrameReader.open() SHALL 优先使用 `stream_url`（通过 cv2.VideoCapture 直连），其次回退到 `build_pull_url()`。

#### Scenario: 自定义流优先
- **WHEN** VideoDevice 有 `stream_url="rtmp://10.0.0.5/live/main"`
- **THEN** FrameReader 直接以该 URL 连接，不调用 build_pull_url
