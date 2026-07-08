## Why

Server 侧当前仅有数据模型骨架，缺少流媒体监控的核心运行时能力——Node 无法通过 WSS 注册并接受指令、音视频流无法被拉取与合并、View 无法被创建与管理。本次变更是将 Server 从"静态模型仓库"升级为"可运行的监控流媒体中枢"。

## What Changes

- **Node WSS 连接管理**：Server 接收 Node 的 WSS 连接，维护 ConnectionRegistry，支持向 Node 发送命令（UPDATE_STREAM、LIST_DEVICES）
- **设备发现**：Node 连接后上报音视频设备列表，Server 写入数据库
- **View CRUD**：创建/查询/删除监控视图，每个 View 绑定一对 (audio, video)
- **推流引用计数**：View 创建/删除时自动管理流生命周期——引用计数为零的发 UPDATE_STREAM 命令启动/停止推流
- **流合并与推 SRS**：Server 用 FFmpeg 从 SRS 拉取 audio+video 原始流，合并为一路 RTMP 后推回 SRS，前端从 SRS 拉流播放
- **模型变更**：VideoDevice/AudioDevice 新增 `streaming` 字段，MonitorView 的 `audio_id` 改为 non-nullable
- **配置扩展**：新增 RTMP、SRS、WSS 相关配置项
- **Schema 层建设**：建立 `src/schema/` 下的 HTTP 请求/响应模型和 WSS 命令协议模型
- **`network/` 目录结构**：将现有的 `src/api/` 重构为 `src/network/api/`、`src/network/wss/`、`src/network/rtmp/` **BREAKING**

## Capabilities

### New Capabilities

- `node-wss-connection`: Node 通过 WSS 连接 Server，Server 维护连接注册表，支持双向命令通信
- `device-discovery`: Node 连接后上报音视频设备列表，Server 将设备信息写入数据库
- `view-management`: 监控视图的 CRUD——选择 audio+video 组成 View，管理流生命周期
- `stream-lifecycle`: 基于 View 引用计数的推流启停逻辑，通过 WSS 向 Node 发送 UPDATE_STREAM 命令
- `stream-merge-srs`: Server 从 SRS 拉取 raw 流，FFmpeg 合并 audio+video，推回 SRS 供前端播放
- `network-layer`: `src/network/` 三层网络传输架构（api/wss/rtmp）

### Modified Capabilities

- `computer-node-model`: 新增 WSS 连接状态相关字段（`is_connected`, `last_seen`），支持连接生命周期追踪
- `video-device-model`: 新增 `streaming` 字段标记推流状态
- `audio-device-model`: 新增 `streaming` 字段标记推流状态
- `monitor-view-model`: `audio_id` 改为 non-nullable（View 必须同时包含音视频）

## Impact

- **目录结构**：`src/api/` → `src/network/`（api/wss/rtmp 三层）
- **新增 `src/network/`**：api/（REST 路由）、wss/（Node WSS handler）、rtmp/（RTMP puller/pusher）
- **新增 `src/schema/`**：http/（请求响应模型）、wss/（命令协议模型）
- **新增 `src/service/`**：node_stream_task + node_stream_module、view_task + view_module
- **新增 `src/repository/`**：node_repo、device_repo、view_repo
- **配置变更**：`config.py` 新增 RTMP_HOST、RTMP_PORT、RTMP_DEBUG、SRS_RTMP_PORT、SRS_HTTP_PORT、WSS_NODE_PORT、WSS_NODE_DEBUG、DEBUG_WEB_STREAM
- **依赖新增**：FFmpeg（子进程管理，音频视频合并）、可能引入 python-ffmpeg 或 subprocess 封装
