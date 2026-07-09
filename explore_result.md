# Explore Result — 全量监控能力架构探索

> 日期：2026-07-08
> 主题：Node 连接、流管理、View 合成、SRS 推流到前端

---

## 1. 现有代码地基

项目已有清晰的分层骨架：

```
src/
├── network/      ← 空壳，等待实现
│   ├── api/      ← REST (HTTP)，面向前端
│   ├── wss/      ← WebSocket，面向 Node 命令通道
│   └── rtmp/     ← RTMP 拉流/推流，对接 SRS
├── models/       ← 14 个模型已定义（Node, VideoDevice, AudioDevice, MonitorView + AI 检测相关）
├── schema/       ← 空壳，等待 Pydantic 模型
├── service/      ← video_task + video_module 占位，其余待建
├── repository/   ← 空壳
└── tests/        ← 仅有 test_health
```

### 现有模型 vs 需求核心表

| 需求表 | 现有模型 | 差异 |
|--------|----------|------|
| Node(NodeID, Token) | `Node(id, token)` ✅ | 缺少 WSS 会话状态字段 |
| VideoDevice(VideoID, VideoName, NodeID) | `VideoDevice(id, name, node_id)` ✅ | 缺少推流状态标记 (`streaming`) |
| AudioDevice(AudioID, AudioName, NodeID) | `AudioDevice(id, name, node_id)` ✅ | 缺少推流状态标记 (`streaming`) |
| MonitorView(ViewID, VideoID, AudioID, cachePath) | `MonitorView(id, video_id, audio_id, cache_path)` ✅ | `audio_id` 当前可空 → **须改为必选** |

---

## 2. 架构全景图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION                                      │
│                                                                              │
│  ┌──────────┐    RTMP push     ┌──────────────────────┐                      │
│  │  Node A   │ ───────────────▶│                      │                      │
│  │ (FFmpeg)  │                 │        SRS           │                      │
│  │           │                 │   (Stream Server)    │                      │
│  │  WSS      │                 │                      │                      │
│  │  client   │                 │  接收 Node 原始流     │                      │
│  └─────┬─────┘                 │  接收 Server 合并流   │                      │
│        │                       │  向前端分发 (HTTP-FLV │                      │
│  ┌─────┴─────┐                 │   / HLS / WebRTC)    │                      │
│  │  Node B   │                 └──────────┬───────────┘                      │
│  │  ...      │                            │                                  │
│  └─────┬─────┘                 ┌──────────┴───────────┐                      │
│        │                       │                      │                      │
│        │                       ▼                      ▼                      │
│        │             RTMP pull (raw)    HTTP-FLV / HLS / WebRTC               │
│        │                       │                      │                      │
│        │              ┌────────┴────────┐    ┌────────┴────────┐             │
│        │              │    Server       │    │    Browser      │             │
│        │              │   (FastAPI)     │    │    (React)      │             │
│        │              │                 │    └─────────────────┘             │
│        │              │ ┌─────────────┐ │                                    │
│        │              │ │  network/rtmp   │ │  RTMP pull raw stream from SRS     │
│        │              │ │  puller     │──│  FFmpeg 合并 audio+video           │
│        │              │ │  pusher     │──│▶ RTMP push merged stream to SRS   │
│        │              │ └──────┬──────┘ │                                    │
│        │              │        │        │                                    │
│        │              │ ┌──────┴──────┐ │                                    │
│        │              │ │  service/   │ │                                    │
│        │              │ └──────┬──────┘ │                                    │
│        │              │        │        │                                    │
│        │              │ ┌──────┴──────┐ │                                    │
│        │              │ │  network/api   │ │◀── 前端 REST API                   │
│        │              │ └─────────────┘ │                                    │
│        │              │                 │                                    │
│        │              │ ┌─────────────┐ │                                    │
│        │              │ │  network/wss    │ │                                    │
│        │              │ │node_handler │ │                                    │
│        │              │ └──────┬──────┘ │                                    │
│        │              └────────┼────────┘                                    │
│        │                       │                                             │
│        │              ┌────────┴────────┐                                    │
│        └──────────────▶│     Nginx      │                                    │
│       WSS (commands)   │  ┌───────────┐ │                                    │
│                        │  │ WSS(node) │ │  Nginx 仅代理：                     │
│                        │  │ HTTP      │ │  · WSS (Node ↔ Server)             │
│                        │  └───────────┘ │  · HTTP (Browser ↔ Server)         │
│                        └────────────────┘  · 无 RTMP 模块                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**数据流总结：**

```
                          ┌─────────────────────────────────────┐
                          │               SRS                   │
                          │         (流媒体中枢)                  │
                          └──────┬──────────────┬───────────────┘
                                 │              │
                    RTMP push    │              │  RTMP pull     HTTP-FLV/HLS/WebRTC
                    (原始流)      │              │  (合并后的流)    (前端播放)
                                 │              │                     │
                    ┌────────────┴──┐    ┌──────┴──────────┐    ┌─────┴──────┐
                    │    Node       │    │     Server       │    │   Browser  │
                    │  (FFmpeg)     │    │   (FastAPI)      │    │  (React)   │
                    └───────┬───────┘    └────────┬─────────┘    └────────────┘
                            │                     │
                            │      WSS            │      REST
                            └──────────┬──────────┘
                                       │
                                ┌──────┴──────┐
                                │    Nginx    │
                                │  HTTP+WSS   │
                                │  (无 RTMP)   │
                                └─────────────┘
```

**SRS 作为中枢的职责：**
- 接收 Node 的 RTMP 原始推流（audio / video）
- 接收 Server 的 RTMP 合并推流（View 流）
- 向前端分发 View 流（HTTP-FLV / HLS / WebRTC）
- 可选：录制存档（配合 `cachePath`）

**Nginx 简化后的职责：**
- HTTP 反向代理（前端 → Server REST API）
- WSS 反向代理（Node ↔ Server 命令通道）
- ~~RTMP 模块~~——移除，全部交给 SRS

**关键变更（相比初版探索）**：
- ~~Node → Nginx RTMP → Server~~ → **Node → SRS（RTMP），Server 从 SRS 拉流**
- ~~Server → Browser 直推 WebRTC~~ → **Server → SRS → Browser**
- ~~Nginx 承担 RTMP~~ → **Nginx 仅 HTTP + WSS 代理，SRS 承担全部流媒体**

---

## 3. 关键设计问题

### 3.1 Node 表：WSS 会话状态该不该入表？

**WSS 连接是瞬态的。** Node 断连、重启、网络抖动，连接就没了。把 `is_connected` / `last_seen` 入 Node 表，本质是**缓存状态的持久化**——好处是 Server 重启后知道哪些 Node 曾经连过，坏处是它是一个 eventually-inconsistent 的状态（Node 实际断了但表里还写着 `connected=true`）。

**建议方案：**

```
Node 表：只存注册信息 (id, token, created_at)
       + 不存连接状态

内存中的 ConnectionRegistry（network/wss 维护）：
       { node_id → WebSocket 连接对象 }
       连接建立 → 写入 registry
       连接断开 → 从 registry 移除
```

前端请求 `listNodes` 时，API 从 ConnectionRegistry 查询在线状态，与 Node 表 join 返回，不需要写库。

> **结论**：按照代码最新的 Sqlite 标准先构建测试用库。

---

### 3.2 推流引用计数

描述中的逻辑本质是一个**引用计数系统**：

- 已经在推流的 audio/video 可以被选，但是会显示告警
- View 建立后，Server 自动发送 `UPDATE_STREAM=true`
- View 删除时，如果对应的流没有 View 在使用，发送 `UPDATE_STREAM=false`

```
┌─────────────────────────────────────────────────────┐
│                                                      │
│  VideoDevice / AudioDevice 表增加字段：                │
│    streaming: bool  (是否正在推流)                    │
│                                                      │
│  不存引用计数 → 实时计算：                             │
│    SELECT COUNT(*) FROM monitor_views                │
│    WHERE video_id = ?                                │
│                                                      │
│  CREATE VIEW 时：                                     │
│    1. count = 查引用计数                              │
│    2. if count == 0 → WSS 发 UPDATE_STREAM=true      │
│       if count > 0  → 告警 "该流已被 N 个 View 使用"   │
│    3. 插入 MonitorView 记录                           │
│                                                      │
│  DELETE VIEW 时：                                     │
│    1. 删除 MonitorView 记录                           │
│    2. count = 查引用计数                              │
│    3. if count == 0 → WSS 发 UPDATE_STREAM=false     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

引用计数实时从 DB 算，避免计数字段和实际数据不一致。监控场景下 View 数量不会特别大，实时算没问题。

---

### 3.3 API/Service 分层

由于架构变更为 Server → SRS → Browser，`network/wss` 的职责大幅简化：

- **Node handler**：命令通道（低频、双向）—— **核心职责保留**
- ~~Web handler~~：不再需要。Server 不直接向 Web 推流，改为向 SRS 推 RTMP。

**建议目录结构：**

```
network/
├── api/                         # REST API（HTTP — 前端请求入口）
│   ├── node_router.py           #   GET /api/v1/nodes, GET /api/v1/nodes/{id}/devices
│   ├── view_router.py           #   POST /api/v1/views, DELETE /api/v1/views/{id}, etc.
│   └── __init__.py
│
├── wss/                         # WebSocket（仅 Node 通信）
│   ├── node_handler.py          #   接收 Node 的 wss 连接请求，维护 ConnectionRegistry
│   │                            #   被 service 调取 → 向 Node 发命令
│   └── __init__.py
│
└── rtmp/                        # RTMP 拉流（从 SRS）+ 推流（向 SRS）
    ├── puller.py                #   从 SRS 拉 Node 的原始流
    ├── pusher.py                #   将合并后的 View 流推到 SRS
    └── __init__.py
```

#### 关于 WSS 与 Swagger / Schema 的关系

**Swagger（OpenAPI）对 WSS 的支持是有限的：**

| | REST (HTTP) | WSS (WebSocket) |
|---|---|---|
| 端点出现在 Swagger UI | ✅ FastAPI 自动 | ✅ `@app.websocket` 会列出来 |
| 请求/响应 schema 自动展示 | ✅ Pydantic → OpenAPI schema | ❌ 不展示消息级协议 |
| Swagger UI "Try it out" | ✅ | ❌ Swagger 不会连 WebSocket |
| Schema 定义复用 Pydantic | ✅ | ✅ 可以——同样的 Pydantic 模型，手写文档 |

根本原因：OpenAPI 规范描述的是 HTTP 请求/响应模型，WebSocket 建立连接后消息协议不在它的描述范围内。

**建议的 Schema 分层策略：**

```
src/schema/
├── http/                    # REST 请求/响应 → Swagger 自动渲染
│   ├── node_schema.py       #   GET /nodes 的 Response
│   ├── view_schema.py       #   POST /views 的 Request/Response
│   └── __init__.py
│
├── wss/                     # WSS 消息协议 → Pydantic 做校验，手写文档
│   ├── node_commands.py     #   UPDATE_STREAM, LIST_DEVICES 等命令格式
│   └── __init__.py
│
└── __init__.py
```

WSS 的 schema 仍然放在 `src/schema/` 下，原因：
- **序列化/反序列化校验**：`UpdateStreamRequest.model_validate(msg)` 在收发消息时做类型保障
- **协议契约**：与 Node 开发者共享，保持消息格式一致
- **可扩展文档**：WSS 命令类型少（当前仅 `UPDATE_STREAM`、`LIST_DEVICES`），用 Pydantic + markdown 文档已足够。如果未来命令复杂度增长，可补 AsyncAPI spec（WebSocket 版的 OpenAPI）

---

### 3.4 View 合成 —— 流合并发生在哪里？

"View 由 audio 和 video 直接合并而成。"

在新架构下（Server → SRS → Browser），合成策略更为明确：

```
方案：Server 端 FFmpeg 合并 + AI 推理后推 SRS

  RTMP(video) ─┐
               │                                     ┌─────────────────┐
               ├─▶ Server FFmpeg 合并 ─▶ 逐帧 ─▶ AI 推理 ─▶ 叠加标注帧 ─▶ RTMP ──▶ SRS ──▶ Browser
  RTMP(audio) ─┘                                     │ (YOLO/SlowFast │
                                                     │  /YAMNet)      │
                                                     └─────────────────┘

  流程：
  1. network/rtmp/puller 从 SRS 拉取 raw audio + raw video
  2. view_module 获取当前 View 的 (video_id, audio_id) 配置
  3. Server 用 FFmpeg 将两路流合并为一路
  4. 逐帧经过 AI 推理管线（目标检测、行为识别、声音分类等）
  5. 将检测结果叠加到帧上（画框、标签等），再编码推 RTMP 到 SRS
  6. 前端直接从 SRS 拉流播放（HTTP-FLV / HLS / WebRTC）

  优点：
  - SRS 负责前端分发，支持多种协议，自带 CDN 能力
  - 前端不需要做音画同步（合并后的流已同步）
  - Server 职责清晰：拉流 → 合并 → AI 推理 → 标注 → 推流
```

#### 为什么必须在 Server 合并，而不是分 track 转发或端侧标注？

后续需要扩展"智能识别"能力（如 YOLO 目标检测、SlowFast 行为识别、YAMNet 声音分类）。

```
       ┌──────────────────────────────────────────────┐
       │  如果分 track 转发（video track + audio track）  │
       │  各自独立到达浏览器：                             │
       │                                              │
       │  · AI 模型跑在 Server → 检测结果在 Server      │
       │  · 但原始帧在 Browser 渲染                     │
       │  · 两个不同步的管道                            │
       │                                              │
       │  ❌ 加框怎么办？                               │
       │     Server 需要截帧 → 推理 → 画框 → 重新编码    │
       │     画了框的帧必须和原始帧是同一帧              │
       │     如果把检测框坐标单独发给前端，              │
       │     前端画框和原始帧之间的延迟不可控            │
       │     → 框漂移、音画不同步                       │
       └──────────────────────────────────────────────┘
```

**所以必须在 Server 合并并统一处理完所有标注后，推一路成品流出去。** SRS 只是一个透明的分发管道，前端只负责播放。

> 这就是为什么 View 由 Server 合并为单流的核心理由——不仅是为了前端简单，更是为了在推流前插入 AI 处理环节。

---

### 3.5 DEBUG 模式统一配置

描述中提到了多种 DEBUG 模式，建议收敛为统一的配置层级：

```python
# config.py 建议新增
class Settings(BaseSettings):
    # ...

    # ── RTMP ──
    RTMP_HOST: str = "127.0.0.1"      # 生产 → SRS IP
    RTMP_PORT: int = 1935              # RTMP 默认端口 (SRS listen)
    RTMP_DEBUG: bool = False           # True → 强制 127.0.0.1

    # ── WSS (Node) ──
    WSS_NODE_PORT: int = 9000          # Node 连接的 WSS 端口
    WSS_NODE_DEBUG: bool = False

    # ── SRS ──
    SRS_RTMP_PORT: int = 1936          # SRS 接收 RTMP 推流的端口
    SRS_HTTP_PORT: int = 8080          # SRS HTTP-FLV / HLS 端口
    SRS_DEBUG: bool = False            # True → 使用本地 SRS 地址

    # ── DEBUG Web 前端 ──
    DEBUG_WEB_STREAM: bool = False     # True → 启动内置极简 Node.js 前端页面
```

`docker-compose.prod.yml` 通过环境变量注入生产值，本地开发用 `.env` 覆盖。

> 注：`WSS_WEB_PORT` 已移除——因为前端不再通过 Server 的 WSS 获取流，而是直接从 SRS 拉流。

---

### 3.6 MonitorView 中 audio_id 的可空性

当前模型中 `audio_id` 是可空的 (`nullable=True`)，但需求描述中说 View 需要"选择一对 (audio, video)"。

> **结论**：不允许空，所有 View 都必须同时包含 audio 和 video。

需要在模型中将 `audio_id` 改为 `nullable=False`。

---

## 4. 后续可探讨的方向

### 4.1 Node 与 Server 的 WSS 命令协议

目前已知命令：
- `UPDATE_STREAM` — 开启/关闭某个流的推流
- `LIST_DEVICES` — 让 Node 上报自己的设备列表

这些命令格式需要进入 `/schema` 统一管理。建议在 `src/schema/` 下建立 `wss_commands.py`，定义请求/响应的 Pydantic 模型：

```python
# 示例：schema/wss_commands.py
from pydantic import BaseModel

class UpdateStreamRequest(BaseModel):
    command: str = "UPDATE_STREAM"
    device_type: str       # "video" | "audio"
    device_id: int
    enable: bool           # True = 开始推流, False = 停止推流

class UpdateStreamResponse(BaseModel):
    success: bool
    message: str | None
```

### 4.2 设备发现流程

Node 上的 VideoDevice 和 AudioDevice 是怎么出现在 Server 数据库里的？

- **方案 A**：Node 连接后主动上报设备列表 ← **已确认**

流程：
```
1. Node 通过 WSS 连接 Server
2. Server 发送 LIST_DEVICES 命令
3. Node 返回 {videos: [{name, ...}], audios: [{name, ...}]}
4. Server 将设备信息写入 video_devices / audio_devices 表
5. 前端查询时直接从 DB 读取
```

### 4.3 前端拉流方式

> **结论**：前端直接从 SRS 拉流。

SRS 支持的协议：
- **HTTP-FLV**：低延迟（~1-3s），适合监控场景
- **HLS**：兼容性好，延迟较高（~5-10s）
- **WebRTC**：超低延迟（<500ms），但 SRS 配置较复杂

推荐默认使用 HTTP-FLV，后续按需开启 WebRTC。

### 4.4 cachePath 的用途

> **结论**：存录像缓存。给配置时长的能力（用于之后开启回放）。

`MonitorView.cache_path` — 指向 SRS 录制或 Server 本地缓存的录像文件路径。后续可支持：
- 配置缓存时长（如保留最近 24 小时的录像）
- 回放接口：前端请求某个时间段的录像

---

## 5. 依赖关系总结

```
前端请求流程：

listNodes ──▶ GET /api/v1/nodes
                 └── service/node_task.py → repository

listVideo ──▶ GET /api/v1/nodes/{id}/videos
                 └── service/node_stream_task.py → repository

listAudio ──▶ GET /api/v1/nodes/{id}/audios
                 └── service/node_stream_task.py → repository

createView ──▶ POST /api/v1/views {audio_id, video_id}
                 └── service/view_task.py
                       ├── view_module (引用计数检查)
                       ├── network/wss/node_handler (发 UPDATE_STREAM=true 给 Node，如果需要)
                       ├── network/rtmp/puller (从 SRS 拉取 raw audio+video)
                       ├── view_module (FFmpeg 合并 audio+video)
                       ├── network/rtmp/pusher (推合并流到 SRS)
                       └── repository (插入 MonitorView)

watchView ──▶ 前端直接从 SRS 拉流 (HTTP-FLV / HLS)
                 Server 不参与此步骤

deleteView ──▶ DELETE /api/v1/views/{id}
                 └── service/view_task.py
                       ├── network/rtmp/pusher (停止向 SRS 推流)
                       ├── view_module (FFmpeg 进程终止)
                       ├── view_module (引用计数检查)
                       ├── network/wss/node_handler (可能发 UPDATE_STREAM=false)
                       └── repository (删除 MonitorView)
```

### Server 内部模块依赖关系

```
                    ┌─────────────┐
                    │  network/api   │  ◀── 前端 REST 请求入口
                    └──────┬──────┘
                           │ 调用
                    ┌──────┴──────┐
                    │   service/  │
                    │  *_task.py  │  ◀── 门户函数
                    └──────┬──────┘
                           │ 调用
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴────┐ ┌─────┴─────┐
        │ *_module  │ │ network/wss│ │ network/rtmp  │
        │ (业务逻辑) │ │(发命令)│ │(拉流/推流) │
        └───────────┘ └────────┘ └───────────┘
              │
              │ 读写
        ┌─────┴─────┐
        │repository │  ◀── 数据访问层
        └───────────┘
```
