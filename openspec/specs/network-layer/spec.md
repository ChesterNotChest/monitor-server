# Network Layer

**Purpose:** 定义 `src/network/` 三层网络传输架构（api / wss / rtmp）的目录结构与职责边界。

## Requirements

### Requirement: 三层网络架构
系统 SHALL 将网络传输层统一放置在 `src/network/` 目录下，按协议分为三个子包：`network/api/`（REST HTTP）、`network/wss/`（WebSocket）、`network/rtmp/`（RTMP 推拉流）。现有的 `src/api/` 目录 SHALL 被迁移到 `src/network/api/`。

#### Scenario: 目录结构完整
- **WHEN** 查看 `src/network/` 目录
- **THEN** 包含 `api/`、`wss/`、`rtmp/` 三个子包，每个子包有 `__init__.py`

#### Scenario: 旧 api 目录已迁移
- **WHEN** 构建完成后
- **THEN** `src/api/` 不存在，所有路由已迁移到 `src/network/api/`

### Requirement: network/api 职责
`network/api/` SHALL 承担 FastAPI Router 的注册，面向前端提供 REST API。SHALL 调用 `service/*_task.py` 的门户函数完成业务逻辑。Router SHALL 不直接操作数据库或调用 RTMP/WSS 网络接口——即使是简单只读列表查询也 SHALL 通过 `*_task.py` 的门户函数包装，以保持分层可读性和一致性。

#### Scenario: API 路由调用 service（写操作）
- **WHEN** 前端请求 `POST /api/v1/views`
- **THEN** Router 解析请求参数，调用 `service/view_task.py` 的对应函数，返回响应

#### Scenario: API 路由调用 service（简单读操作）
- **WHEN** 前端请求 `GET /api/v1/nodes`
- **THEN** Router 调用 `service/node_task.py` 的 `list_nodes()` 门户函数（该函数内部调用 `node_repo.get_all()`），而非在 Router 中直接操作 repository

### Requirement: network/wss 职责
`network/wss/` SHALL 承担与 Node 的 WebSocket 通信。SHALL 接收 Node 的连接请求，维护 ConnectionRegistry。SHALL 被 `service/` 模块调取向 Node 发送命令。SHALL 不包含业务逻辑。

#### Scenario: Service 模块通过 wss handler 发送命令
- **WHEN** `view_task.py` 需要向 Node 发送 `UPDATE_STREAM` 命令
- **THEN** 调用 `network/wss/node_handler.py` 的 `send_command()` 方法，不直接操作 WebSocket 对象

### Requirement: network/rtmp 职责
`network/rtmp/` SHALL 承担 RTMP 流的拉取和推送。`puller.py` SHALL 负责构建拉流地址并监测流可用性。`pusher.py` SHALL 负责构建推流地址。FFmpeg 子进程管理 SHALL 由 `service/view_module/` 负责，`network/rtmp/` 仅提供地址构建和辅助方法。

#### Scenario: rtmp 模块构建拉流地址
- **WHEN** 需要获取 video_id=1 的拉流地址
- **THEN** `network/rtmp/puller.py` 的 `build_pull_url(device_type="video", device_id=1)` 返回完整 RTMP URL
