# Part A — 基础层

> **负责人**: ___
> **目标**: 建好所有底层依赖——模型、配置、Schema、Repository、Network 层。
> **交付后**: Part B 可在此基础上构建 Service 和 API 路由。

## 1. 模型变更

- [ ] 1.1 Node 模型新增 `is_connected`（Boolean，默认 false）和 `last_seen`（DateTime，可空）字段
- [ ] 1.2 VideoDevice 模型：新增 `streaming`（Boolean，默认 false）字段；将 `name` 的 `unique=True` 改为 `UniqueConstraint("node_id", "name")` 联合唯一约束（不同 Node 可有同名设备）
- [ ] 1.3 AudioDevice 模型：新增 `streaming`（Boolean，默认 false）字段；将 `name` 的 `unique=True` 改为 `UniqueConstraint("node_id", "name")` 联合唯一约束
- [ ] 1.4 MonitorView 模型 `audio_id` 改为 `nullable=False`
- [ ] 1.5 更新 `src/models/__init__.py` 导入，确保 `Base.metadata.create_all` 生效（新字段 + 新约束）

## 2. 配置扩展

- [ ] 2.1 `config.py` 新增 RTMP 配置：`RTMP_HOST`、`RTMP_PORT`、`RTMP_DEBUG`
- [ ] 2.2 `config.py` 新增 SRS 配置：`SRS_RTMP_PORT`、`SRS_HTTP_PORT`、`SRS_HOST`
- [ ] 2.3 `config.py` 新增 WSS 配置：`WSS_NODE_PORT`、`WSS_NODE_DEBUG`
- [ ] 2.4 `config.py` 新增 `DEBUG_WEB_STREAM` 开关（预留，本次不实现）
- [ ] 2.5 `.env` 添加新配置项的默认值

## 3. Schema 层

- [ ] 3.1 创建 `src/schema/http/` 包，包含 `__init__.py`
- [ ] 3.2 创建 `src/schema/http/node_schema.py`：Node 列表/详情 Response 模型
- [ ] 3.3 创建 `src/schema/http/view_schema.py`：View 创建 Request、View 列表/详情 Response 模型
- [ ] 3.4 创建 `src/schema/wss/` 包，包含 `__init__.py`
- [ ] 3.5 创建 `src/schema/wss/node_commands.py`：`ConnectRequest`（node token）、`ConnectResponse`（session_token + videos 列表 + audios 列表）、`UpdateStreamRequest`（`device_type`、`device_id`、`enable`）、`UpdateStreamResponse` Pydantic 模型。注：`device_id` 泛指 audio_id / video_id

## 4. Repository 层

- [ ] 4.1 创建 `src/repository/node_repo.py`：按 id/token 查 Node（token 存 SHA256 hash，查询时对输入做 hash 后匹配）、查全部 Node、更新连接状态、按 node_id 查询设备并批量更新 streaming 状态（供断连级联清理使用）
- [ ] 4.2 创建 `src/repository/device_repo.py`：按 node_id 查 VideoDevice/AudioDevice 列表、按 device_type + device_id 查单个设备、upsert 设备（基于 (node_id, name) 联合唯一判重）、更新 streaming 字段
- [ ] 4.3 创建 `src/repository/view_repo.py`：创建 View、按 id 删 View、查全部 View、按 id 查 View、查引用计数（`count_by_video_id` / `count_by_audio_id`）
- [ ] 4.4 更新 `src/repository/__init__.py`：导入并导出三个 repo 模块

## 5. Network 层 — 迁移与新建

- [ ] 5.1 创建 `src/network/` 包结构（`api/`、`wss/`、`rtmp/` 三个子包，各含 `__init__.py`）
- [ ] 5.2 将现有 `src/api/` 内容迁移到 `src/network/api/`，删除 `src/api/`
- [ ] 5.3 创建 `src/network/wss/node_handler.py`：WebSocket 端点（接收 Node 连接，首条消息校验 token，查该 Node 下已有设备列表，返回 `ConnectResponse{session_token, videos, audios}`）、ConnectionRegistry 类（内存 `{node_id: WebSocket}` 映射）、`send_command()` 异步方法（向指定 Node 发 JSON 命令并等响应）、**断连回调中级联清理**：更新 Node `is_connected=false` + 该 Node 下所有设备 `streaming=false` + 从 registry 移除
- [ ] 5.4 创建 `src/network/rtmp/puller.py`：`build_pull_url(device_name, device_type, device_id)` 地址构建函数，格式 `rtmp://{host}:{port}/live/{device_name}_{device_type}_{device_id}`
- [ ] 5.5 创建 `src/network/rtmp/pusher.py`：`build_push_url(view_id)` 和 `build_play_urls(view_id)` 地址构建函数

---

## Part A → Part B 接口契约

以下接口是 Part B 依赖的，Part A 完成后需要稳定：

| 模块 | 接口 | 说明 |
|------|------|------|
| `models/*.py` | Node/VideoDevice/AudioDevice/MonitorView 类 | 新字段 + 联合唯一约束就位 |
| `config.py` | `settings.RTMP_*`, `settings.SRS_*`, `settings.WSS_*` | 所有配置项可用 |
| `repository/node_repo.py` | `get_all()`, `get_by_id()`, `get_by_token()`, `update_connection_status()`, `reset_device_streaming_by_node(node_id)` — 断连级联清理用 | |
| `repository/device_repo.py` | `get_videos_by_node()`, `get_audios_by_node()`, `get_device_by_id()`, `upsert_device()`, `update_streaming()` | |
| `repository/view_repo.py` | `create()`, `delete()`, `get_all()`, `get_by_id()`, `count_by_video_id()`, `count_by_audio_id()` | |
| `schema/http/*.py` | NodeResponse, ViewCreateRequest, ViewResponse | Pydantic 模型 |
| `schema/wss/node_commands.py` | ConnectRequest, ConnectResponse, UpdateStreamRequest, UpdateStreamResponse | 连接握手 + 流控制 |
| `network/wss/node_handler.py` | `ConnectionRegistry.get()`, `send_command()` | |
| `network/rtmp/puller.py` | `build_pull_url(device_name, device_type, device_id)` | 命名：`{name}_{type}_{id}` |
| `network/rtmp/pusher.py` | `build_push_url(view_id)`, `build_play_urls(view_id)` | |
