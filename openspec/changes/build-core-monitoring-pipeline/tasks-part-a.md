# Part A — 基础层

> **负责人**: ___
> **目标**: 建好所有底层依赖——模型、配置、Schema、Repository、Network 层。
> **交付后**: Part B 可在此基础上构建 Service 和 API 路由。

## 1. 模型变更

- [x] 1.1 Node 模型新增 `is_connected`（Boolean，默认 false）和 `last_seen`（DateTime，可空）字段
- [x] 1.2 VideoDevice 模型：新增 `streaming`（Boolean，默认 false）字段；将 `name` 的 `unique=True` 改为 `UniqueConstraint("node_id", "name")` 联合唯一约束（不同 Node 可有同名设备）
- [x] 1.3 AudioDevice 模型：新增 `streaming`（Boolean，默认 false）字段；将 `name` 的 `unique=True` 改为 `UniqueConstraint("node_id", "name")` 联合唯一约束
- [x] 1.4 MonitorView 模型 `audio_id` 改为 `nullable=False`
- [x] 1.5 更新 `src/models/__init__.py` 导入，确保 `Base.metadata.create_all` 生效（新字段 + 新约束）

## 2. 配置扩展

- [x] 2.1 `config.py` 新增 RTMP 配置：`RTMP_HOST`、`RTMP_PORT`、`RTMP_DEBUG`
- [x] 2.2 `config.py` 新增 SRS 配置：`SRS_RTMP_PORT`、`SRS_HTTP_PORT`、`SRS_HOST`
- [x] 2.3 `config.py` 新增 WSS 配置：`WSS_NODE_PORT`、`WSS_NODE_DEBUG`
- [x] 2.4 `config.py` 新增 `DEBUG_WEB_STREAM` 开关（默认 false）。启用后 FFmpeg 将合并后的 View 流推到本地 Node.js RTMP 靶子（`rtmp://127.0.0.1:1936/view/{view_id}`），而非 SRS。配合 Node 项目已有的 `rtmp_server/index.js`（node-media-server），可用 OBS 直接拉流验证。**本次实现**——启动/停止 RTMP 靶子子进程的逻辑
- [x] 2.5 `.env` 添加新配置项的默认值

## 3. Schema 层

- [x] 3.1 创建 `src/schema/http/` 包，包含 `__init__.py`
- [x] 3.2 创建 `src/schema/http/node_schema.py`：Node 列表/详情 Response 模型
- [x] 3.3 创建 `src/schema/http/view_schema.py`：View 创建 Request、View 列表/详情 Response 模型
- [x] 3.4 创建 `src/schema/wss/` 包，包含 `__init__.py`
- [x] 3.5 创建 `src/schema/wss/node_commands.py`：`ConnectRequest`（node token）、`ConnectResponse`（session_token + videos 列表 + audios 列表）、`UpdateStreamRequest`（`device_type`、`device_id`、`enable`）、`UpdateStreamResponse` Pydantic 模型。注：`device_id` 泛指 audio_id / video_id

## 4. Repository 层 — 扩展已有类

> 仓库已有 `BaseRepo[T]` 泛型基类 + `NodeRepo`、`VideoDeviceRepo`、`AudioDeviceRepo`、`MonitorViewRepo` 四个具体类。本节在现有类上追加方法，不新建文件。

- [x] 4.1 `NodeRepo` 追加方法：`update_connection_status(node_id, is_connected, last_seen)` — 更新连接状态和最后活跃时间；`reset_device_streaming_by_node(node_id)` — 断连级联清理，将该 Node 下所有设备 `streaming=false`。token 存储 SHALL 做 SHA256 hash（存入时 hash，`by_token()` 比对时对输入 hash 后匹配）
- [x] 4.2 `VideoDeviceRepo` 追加方法：`upsert(node_id, name)` — 基于 `(node_id, name)` 联合唯一判重，存在跳过、不存在 INSERT；`update_streaming(device_id, streaming: bool)` — 更新推流状态。`AudioDeviceRepo` 追加相同方法
- [x] 4.3 `MonitorViewRepo` 追加方法：`count_by_video_id(video_id) -> int` — 引用计数；`count_by_audio_id(audio_id) -> int` — 引用计数。现有 `device_in_use()` 返回 bool，需新增计数版本

## 5. Network 层 — 迁移与新建

- [x] 5.1 创建 `src/network/` 包结构（`api/`、`wss/`、`rtmp/` 三个子包，各含 `__init__.py`）
- [x] 5.2 将现有 `src/api/` 内容迁移到 `src/network/api/`，删除 `src/api/`
- [x] 5.3 创建 `src/network/wss/node_handler.py`：WebSocket 端点（接收 Node 连接，首条消息校验 token，查该 Node 下已有设备列表，返回 `ConnectResponse{session_token, videos, audios}`）、ConnectionRegistry 类（内存 `{node_id: WebSocket}` 映射）、`send_command()` 异步方法（向指定 Node 发 JSON 命令并等响应）、**断连回调中级联清理**：更新 Node `is_connected=false` + 该 Node 下所有设备 `streaming=false` + 从 registry 移除
- [x] 5.4 创建 `src/network/rtmp/puller.py`：`build_pull_url(device_name, device_type, device_id)` 地址构建函数，格式 `rtmp://{host}:{port}/live/{device_name}_{device_type}_{device_id}`
- [x] 5.5 创建 `src/network/rtmp/pusher.py`：`build_push_url(view_id)` — 生产推 SRS `rtmp://{host}:{srs_port}/view/{id}`；`DEBUG_WEB_STREAM=true` 时推本地靶子 `rtmp://127.0.0.1:1936/view/{id}`。`build_play_urls(view_id)` — 生产返回 SRS HTTP-FLV/WebRTC 地址，debug 模式返回本地 RTMP 地址供 OBS 使用

---

## Part A → Part B 接口契约

以下接口是 Part B 依赖的，Part A 完成后需要稳定：

| 模块 | 接口（类.方法 形式） | 说明 |
|------|------|------|
| `models/*.py` | Node/VideoDevice/AudioDevice/MonitorView 类 | 新字段 + 联合唯一约束就位 |
| `config.py` | `settings.RTMP_*`, `settings.SRS_*`, `settings.WSS_*` | 所有配置项可用 |
| `repository/node_repo.py` | `NodeRepo(db).all()`, `.get(id)`, `.by_token(t)`, `.create(**kw)`, `.update_connection_status()`, `.reset_device_streaming_by_node()` | 继承 BaseRepo |
| `repository/video_device_repo.py` | `VideoDeviceRepo(db).by_node(nid)`, `.get(id)`, `.upsert(nid, name)`, `.update_streaming(id, bool)` | 继承 BaseRepo |
| `repository/audio_device_repo.py` | `AudioDeviceRepo(db).by_node(nid)`, `.get(id)`, `.upsert(nid, name)`, `.update_streaming(id, bool)` | 继承 BaseRepo |
| `repository/monitor_view_repo.py` | `MonitorViewRepo(db).create(**kw)`, `.delete(id)`, `.all()`, `.get(id)`, `.count_by_video_id()`, `.count_by_audio_id()` | 继承 BaseRepo |
| `schema/http/*.py` | NodeResponse, ViewCreateRequest, ViewResponse | Pydantic 模型 |
| `schema/wss/node_commands.py` | ConnectRequest, ConnectResponse, UpdateStreamRequest, UpdateStreamResponse | 连接握手 + 流控制 |
| `network/wss/node_handler.py` | `ConnectionRegistry.get()`, `send_command()` | |
| `network/rtmp/puller.py` | `build_pull_url(device_name, device_type, device_id)` | 命名：`{name}_{type}_{id}` |
| `network/rtmp/pusher.py` | `build_push_url(view_id)`, `build_play_urls(view_id)` | |
