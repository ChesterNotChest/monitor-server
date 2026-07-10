# Local Dev E2E Paradigm

**Purpose:** 定义本地开发联调的固定范式——Node 作为统一拉流工具，Server 作为 AI 处理端，无需 SRS/Docker。

## ADDED Requirements

### Requirement: 统一拓扑
本地联调 SHALL 使用以下拓扑，不依赖 SRS 或 Docker：

```
Camera/Mic → Node(FFmpeg 推流) → RTMP :1935 → Server(拉流+AI推理) → RTMP :1936 → VLC/OBS
(原始流)                                    (标注流)
```

- Node 推原始流到 `rtmp://127.0.0.1:1935/live/{device_name}_{device_type}_{device_id}`
- Server 从 :1935 拉流，AI 推理后推标注流到 `rtmp://127.0.0.1:1936/view/{view_id}`
- 开发者用 VLC/OBS 拉标注流观看

### Requirement: 固定配置

#### 模式一：单 Node 推流 + 手动拉流（Demo 验证）
Node 独立运行，不连 Server。开发者手动 VLC 拉流确认画面。

| 变量 | 值 | 说明 |
|---|---|---|
| `RTMP_DEBUG` | `true` | 启动内嵌 RTMP Server :1935，推所有设备 |
| `DEBUG_WSS` | `true` | 使用 mock WSS，不连真实 Server |

```bash
cd monitor-node
set RTMP_DEBUG=true
set DEBUG_WSS=true
python -m src.run
# → VLC 打开 rtmp://127.0.0.1:1935/live/{device_name}_{device_type}_{device_id}
```

#### 模式二：Node + Server 完整联调
Node 连接真实 Server，Server 拉流做 AI 推理并推标注流。这是标准本地联调模式。

**Node 侧：**

| 变量 | 值 | 说明 |
|---|---|---|
| `RTMP_DEBUG` | `true` | 启动内嵌 RTMP Server :1935，推所有设备 |
| `DEBUG_WSS` | `false` | 连接真实 Server WSS |
| `SERVER_BASE_URL` | `127.0.0.1` | 指向本地 Server |
| `WSS_PORT` | `8000` | Server HTTP/WSS 端口（非默认 8443） |

**Server 侧：**

| 变量 | 值 | 说明 |
|---|---|---|
| `DEBUG_WEB_STREAM` | `true` | 启动 rtmp_debug_server.js :1936 |
| `RTMP_DEBUG` | `true` | 从 127.0.0.1:1935 拉流 |

### Requirement: 固定启动流程
本地联调 SHALL 按以下顺序启动：

**Terminal 1 — Node（推流端）：**
```bash
cd monitor-node
set RTMP_DEBUG=true
set DEBUG_WSS=false
set SERVER_BASE_URL=127.0.0.1
set WSS_PORT=8000
python run.py
```
自动：枚举设备 → WSS 连接 Server :8000 → 设备注册 → 启动 Node.js RTMP Server :1935 → FFmpeg 推所有设备

**Terminal 2 — Server（拉流处理端）：**
```bash
cd monitor-server
set DEBUG_WEB_STREAM=true
set RTMP_DEBUG=true
python -m src.run
```
自动：DB 建表 + seed admin → 启动 rtmp_debug_server.js :1936 → WSS 接受 Node 连接 → 设备同步 → 等待 View 创建 → AI 推理标注 → 推标注流

### Requirement: 验收 Checklist
每次联调 SHALL 通过以下验收：

- [ ] Terminal 1 Node 启动成功，日志打印 `[RTMP_DEBUG] 拉流地址: rtmp://127.0.0.1:1935/live/{device_name}_{device_type}_{device_id}`
- [ ] VLC 打开 Node 日志中的拉流地址，确认原始画面可用
- [ ] Terminal 2 Server 启动成功，WSS 连接 Node
- [ ] Swagger `POST /api/v1/views` 创建 View 成功
- [ ] VLC 打开 `rtmp://127.0.0.1:1936/view/{view_id}` 确认标注画面可用
- [ ] 标注画面包含 YOLO 检测框 + 时间戳
- [ ] （Part B 已合入时）标注画面包含 Person tracking ID
- [ ] （Part C 已合入时）违禁事件触发后 `/api/v1/events` 可查到 SituationEvent
- [ ] CTRL+C 关闭两个终端，进程完全退出，无僵尸 FFmpeg

### Requirement: Demo 脚本位置
手动执行的演示/验证脚本 SHALL 放置在 `tools/` 目录，命名为 `<name>_demo.py`（如 `live_camera_demo.py`、`yamnet_live_demo.py`），不以 `test_` 为前缀。
