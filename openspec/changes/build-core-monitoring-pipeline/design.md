## Context

Server 当前仅有 SQLAlchemy 数据模型骨架和 FastAPI 框架初始化，缺少流媒体监控的核心运行时能力。本次设计需要构建从 Node WSS 连接、设备发现、View 管理、流合并到推 SRS 的完整管线。

关键约束：
- Node 没有公网 IP，由 Node 主动向 Server 建立 WSS 连接
- 所有 RTMP 流以 SRS 为中枢——Node 推到 SRS，Server 从 SRS 拉，合并后推回 SRS，前端从 SRS 播放
- Nginx 仅负责 HTTP + WSS 代理
- 后续需在 Server 侧插入 AI 推理管线（目标检测、行为识别），架构需预留帧处理插入点
- 当前使用 SQLite 数据库，后续可切换 PostgreSQL

## Goals / Non-Goals

**Goals:**
- 建立 `src/network/` 三层网络架构（api / wss / rtmp）
- Node 通过 WSS 连接 Server，完成 token 认证，维护 ConnectionRegistry
- Node 连接后上报音视频设备列表，Server 写入数据库
- View CRUD：创建 View 时绑定 (audio, video) 对，自动触发推流
- 流生命周期管理：基于 View 引用计数的 UPDATE_STREAM 命令
- Server 用 FFmpeg 从 SRS 拉流、合并 audio+video、推回 SRS
- 配置系统覆盖生产/Debug 场景（RTMP、SRS、WSS）
- Schema 层建设：HTTP 请求/响应模型 + WSS 命令协议模型

**Non-Goals:**
- Node 侧实现（仅需要 Server 侧的协议对端）
- Web 前端实现（仅需要 Server 提供 API）
- AI 推理管线（目标检测/行为识别）——本次仅预留流水线插入点
- 录像回放功能（cachePath 存储能力后续实现）
- DEBUG_WEB_STREAM 内置前端（后续实现）
- 用户认证与权限系统

## Decisions

### 1. `network/` 三层架构

```
src/network/
├── api/          # REST (HTTP) — FastAPI Router，面向前端
├── wss/          # WebSocket — Node 命令通道
└── rtmp/         # RTMP 拉流/推流 — 对接 SRS
```

**理由**：三种协议的共性是"网络传输"，放在同一父目录下消除歧义。旧的 `src/api/` 命名模糊——api 指 REST 还是全部？ `network/api` 明确是 HTTP API。

**替代方案**：保持 `api/http`、`api/wss`、`api/rtmp`（已否决——api 歧义过大）。

### 2. WSS 连接状态：ConnectionRegistry（内存） + Node 表字段

Node 表新增两个字段：

- `is_connected`（bool）：当前 WSS 连接状态
- `last_seen`（datetime）：最后活跃时间

同时在内存中维护 ConnectionRegistry：

```
{ node_id → WebSocket 连接对象 }
```

连接建立 → 更新 DB `is_connected=True` + 写入 registry
连接断开 → 更新 DB `is_connected=False, last_seen=now()` + 级联将该 Node 下所有 `streaming=true` 的设备设为 `false` + 从 registry 移除

**理由**：混合策略。内存 registry 用于快速查 WebSocket 对象发命令；DB 字段用于 API 返回在线状态（无需每次查 registry）。字段入 DB 解决了 Server 重启后知道哪些 Node 曾经连过的问题，但通过 `is_connected` + `last_seen` 可以识别过期状态。

**替代方案**：纯内存（不存库）——Server 重启丢失所有连接历史；纯 DB（不存内存）——每次发命令需要把 WebSocket 对象序列化，不可行。

### 3. 推流引用计数：实时 DB 查询

不存储引用计数字段，每次 CREATE/DELETE View 时实时查询：

```sql
SELECT COUNT(*) FROM monitor_views WHERE video_id = ?
SELECT COUNT(*) FROM monitor_views WHERE audio_id = ?
```

**理由**：避免计数与实际数据不一致。监控场景下 View 数量有限（几十到几百），COUNT 查询性能足够。

**替代方案**：在 VideoDevice/AudioDevice 上维护 `view_count` 字段——需要事务保证一致性，SQLite 并发写入能力有限，容易出 bug。

### 4. FFmpeg 子进程管理

每个 View 合并任务对应一个 FFmpeg 子进程：

```
ffmpeg -i rtmp://srs:1935/live/{device_name}_video_{video_id} \
       -i rtmp://srs:1935/live/{device_name}_audio_{audio_id} \
       -c:v copy -c:a aac \
       -f flv rtmp://srs:1935/view/{view_id}
```

在 `src/network/rtmp/` 中封装子进程管理：

- `puller.py`：从 SRS 拉流（FFmpeg input）
- `pusher.py`：向 SRS 推流（FFmpeg output）
- 合并逻辑在 `view_module` 中调用 FFmpeg 一根命令完成拉取+合并+推送

使用 `asyncio.create_subprocess_exec` 管理进程生命周期，View 删除时 SIGTERM 终止。

**理由**：每个 View 独立进程，互不干扰。c:v copy 避免视频重编码，仅音频转 AAC，CPU 开销可控。

**替代方案**：使用 FFmpeg Python binding——增加依赖，灵活性不如 subprocess；GStreamer——Windows 兼容性差。

### 5. RTMP 推流命名规约

Node 向 SRS 推流时，流名 SHALL 遵循格式：

```
{device_name}_{device_type}_{device_id}
```

示例：`cam0_video_1`、`mic0_audio_2`

**理由**：流名需要同时包含设备名称（方便 Node 侧 FFmpeg 定位设备）和设备 ID（方便 Server 侧定位数据库记录）。`device_id` 是全局唯一的，所以流名实际也是全局唯一的。

**替代方案**：`{device_type}_{device_id}`（如 `video_1`）——缺少设备名称，Node 侧 FFmpeg 无法区分同类型的不同物理设备。

### 6. 代码约定：占位文件 docstring

新建的 Python 包或模块的占位文件（不含具体逻辑的 `__init__.py` 或预留模块）SHALL 在文件顶部包含中文 docstring 说明该模块的预期职责。例如：

```python
'''
一个 task 有一个自己的 module。task 为门户，module 为详细逻辑的放置位置。
'''
```

已理解架构设计规范且切实无需保留的旧占位文件 SHALL 被删除，不作为示例保留。

### 7. WSS 命令协议格式

JSON over WebSocket，请求/响应模式。

**连接握手（Node → Server → Node）：**

```json
// Node → Server（首条消息）
{"token": "abc123"}

// Server → Node（认证成功响应）
{
  "session_token": "sess_xxx",
  "videos": [{"id": 1, "name": "cam0"}],
  "audios": [{"id": 2, "name": "mic0"}]
}
```

Node 收到后本地建立映射表 `{1 → "cam0", 2 → "mic0"}`，供后续 `UPDATE_STREAM` 反查。

**命令交互（后续消息，请求/响应模式）：**

```json
// Server → Node
{"command": "UPDATE_STREAM", "device_type": "video", "device_id": 1, "enable": true}

// Node → Server
{"success": true, "message": null}
```

Node 在连接握手时已获得 `(device_id → device_name)` 映射表，因此 `UPDATE_STREAM` 只需传 `device_type` + `device_id`，Node 自行反查物理设备名称后构造 RTMP 推流地址 `{device_name}_{device_type}_{device_id}`。

命令定义放在 `src/schema/wss/node_commands.py`，用 Pydantic 模型做序列化/反序列化校验。WSS 端点会出现在 FastAPI Swagger 页面，但消息级协议不会自动文档化——当前命令数量少，用 Pydantic + markdown 文档即可。

### 8. SRS 作为流媒体中枢

```
Node ──RTMP push──▶ SRS (原始流)
Server ◀──RTMP pull── SRS
Server ──RTMP push──▶ SRS (合并后的 View 流)
Browser ◀──HTTP-FLV/WebRTC── SRS
```

**理由**：SRS 处理所有流媒体分发，Server 只做业务逻辑和流处理。Nginx 简化为纯 HTTP+WSS 代理。后续 AI 推理在 Server 的 FFmpeg 管线中插入帧处理环节即可。

**替代方案**：Server 直接向前端推 WebRTC——Server 需要管理大量 P2P 连接，超出 FastAPI 的能力范围。

### 9. Schema 层分家

```
src/schema/
├── http/                    # REST 请求/响应 → Swagger 自动渲染
│   ├── node_schema.py
│   ├── view_schema.py
│   └── __init__.py
├── wss/                     # WSS 消息协议 → Pydantic 校验 + 手写文档
│   ├── node_commands.py
│   └── __init__.py
└── __init__.py
```

**理由**：OpenAPI 不描述 WebSocket 消息级协议，HTTP schema 和 WSS schema 受众不同（前者 Swagger 渲染，后者作为代码契约）。分开放置避免混淆。

## Risks / Trade-offs

- **FFmpeg 子进程泄漏**：View 删除或 Server 崩溃时子进程未清理 → 用 `atexit` + View 删除时显式 SIGTERM，定期检查孤儿进程
- **SRS 单点故障**：SRS 宕机所有流中断 → 生产环境 SRS 做 HA（非本次范围）；健康检查接口暴露 SRS 连通性
- **引用计数竞态**：并发 CREATE/DELETE 同一 View 时计数不准 → 在 `view_task` 层面加数据库事务，同一流的操作串行化
- **SQLite 并发限制**：多 View 并发写入可能锁争用 → 当前 View 数量有限，SQLite WAL 模式可缓解；后续切 PostgreSQL 彻底解决
- **WSS 断连状态不一致**：Node 异常断连时 DB 中 `is_connected` 仍为 true → WebSocket 断开回调中更新 DB 并级联清理设备 `streaming` 状态，同时 `last_seen` 用于定时清理僵尸状态
- **delete_view 事务边界**：FFmpeg 终止失败不应影响 DB 一致性 → 先删 DB 记录（事务保护），成功后再杀 FFmpeg（失败仅记日志）

## Open Questions

- DEBUG_WEB_STREAM 模式的内置前端具体形式（静态 HTML 页面 vs 独立 Node.js 进程）——非本次范围
- FFmpeg 推流到 SRS 失败时的重试策略（立即重试 vs 指数退避）——实现时确定
- WSS 命令是否需要超时重发机制——先不做，Node 侧保证响应
- **Token 存储安全**：`nodes.token` 应存 SHA256 hash 而非明文——本次实现时在 repository 层做 hash 后存储即可，不影响 API 契约
- **消息级签名（非本次范围）**：未来可引入非对称加密增强安全性。Server 部署时在配置指定私钥路径，Node 部署时人工放置公钥。Server 对关键命令（如 UPDATE_STREAM）用私钥签名，Node 用公钥验签。当前 WSS + TLS 传输层加密已覆盖基础安全需求，消息签名作为后续增强
