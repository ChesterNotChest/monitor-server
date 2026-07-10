# Local Dev E2E Paradigm

**Purpose:** 定义本地开发联调的固定范式——Node 作为统一推流工具，Server 作为 AI 处理端，无需 SRS/Docker。

## Requirements

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
python run.py
# → VLC 打开 rtmp://127.0.0.1:1935/live/{device_name}_{device_type}_{device_id}
```

#### 模式二：Node + Server 按需联调（标准模式）
Node 连接真实 Server，但**不自动推流**。通过 API 创建 View 时，Server 发送 WSS UPDATE_STREAM 命令，Node 按需启动对应设备。RTMP 服务器需手动启动。

**Terminal 0 — RTMP 服务器（前置）**
```bash
cd monitor-node/rtmp_server
npm install        # 首次
node index.js
# → Node Media Rtmp Server started on port: 1935
```

**Terminal 1 — Node（等待 Server 命令）**

| 变量 | 值 | 说明 |
|---|---|---|
| `RTMP_DEBUG` | `false` | 不自动推流，等待 Server 命令 |
| `DEBUG_WSS` | `false` | 连接真实 Server WSS |
| `SERVER_BASE_URL` | `127.0.0.1` | 指向本地 Server |
| `WSS_PORT` | `8000` | Server WSS 端口 |
| `RTMP_PORT` | `1935` | 推流目标端口 |

```bash
cd monitor-node
set RTMP_DEBUG=false
set DEBUG_WSS=false
set SERVER_BASE_URL=127.0.0.1
set WSS_PORT=8000
set RTMP_PORT=1935
python run.py
```

**Terminal 2 — Server（拉流处理）**

| 变量 | 值 | 说明 |
|---|---|---|
| `DEBUG_WEB_STREAM` | `true` | 启动 rtmp_debug_server.js :1936 |
| `RTMP_DEBUG` | `true` | 从 127.0.0.1:1935 拉流 |

```bash
cd monitor-server
set DEBUG_WEB_STREAM=true
set RTMP_DEBUG=true
python -m src.run
```

### Requirement: 固定启动流程
本地联调 SHALL 按以上顺序启动三个终端：

1. Terminal 0 — RTMP 服务器（先启动，作为推/拉流中转）
2. Terminal 2 — Server（WSS 端，等待 Node 注册）
3. Terminal 1 — Node（WSS 客户端，注册后等待命令）

### Requirement: 验收 Checklist
每次联调 SHALL 通过以下验收：

- [ ] Terminal 0 RTMP 服务器启动成功，日志显示 `Node Media Rtmp Server started on port: 1935`
- [ ] Terminal 2 Server 启动成功，`curl http://127.0.0.1:8000/health` 返回 `{"status":"ok"}`
- [ ] Terminal 1 Node 启动成功，日志显示 `WSS authenticated, session_token=...`
- [ ] Swagger `POST /api/v1/views` 创建 View 成功
- [ ] 创建 View 后，Node 日志显示对应设备的 `【xxx】已连接`
- [ ] `GET /api/v1/nodes/1/videos` 中对应设备 `streaming: true`
- [ ] VLC 打开 `rtmp://127.0.0.1:1936/view/{view_id}` 确认标注画面可用
- [ ] 标注画面包含 YOLO 检测框 + 时间戳
- [ ] （Part B 已合入时）标注画面包含 Person tracking ID
- [ ] （Part C 已合入时）违禁事件触发后 `/api/v1/events` 可查到 SituationEvent
- [ ] CTRL+C 关闭三个终端，进程完全退出，无僵尸 FFmpeg

### Requirement: 模式二 API 验证序列
完成固定启动流程后，SHALL 通过以下 API 调用确认 Node-Server 联调状态。以下示例使用 curl，`$TOKEN` 通过 `/auth/login` 获取。

**1. 确认 Node 已注册**
```bash
curl http://127.0.0.1:8000/api/v1/nodes/ -H "Authorization: Bearer $TOKEN"
# → {"nodes":[{"id":1,"is_connected":true,"last_seen":"..."}]}
```

**2. 确认设备列表（首次心跳后）**
```bash
curl http://127.0.0.1:8000/api/v1/nodes/1/videos -H "Authorization: Bearer $TOKEN"
# → {"videos":[{"id":1,"name":"USB webcam","node_id":1,"streaming":false}]}
curl http://127.0.0.1:8000/api/v1/nodes/1/audios -H "Authorization: Bearer $TOKEN"
# → {"audios":[{"id":1,"name":"麦克风 (Realtek(R) Audio)","node_id":1,"streaming":false}]}
```
注意：此时 `streaming` 为 `false`——设备已注册但未推流。

**3. 创建 View（触发推流）**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/views/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":1,"audio_id":1}'
# → {"id":1,"video_id":1,"audio_id":1,"rtmp_url":"rtmp://127.0.0.1:1936/view/1",...}
```

**4. 确认推流状态变更**
```bash
curl http://127.0.0.1:8000/api/v1/nodes/1/videos -H "Authorization: Bearer $TOKEN"
# → streaming: true  ← View 创建后自动变为 true
```

**5. 播放标注流**
- VLC/OBS 打开 `rtmp_url`（如 `rtmp://127.0.0.1:1936/view/1`）

### Requirement: Demo 脚本位置
手动执行的演示/验证脚本 SHALL 放置在 `tools/` 目录，命名为 `<name>_demo.py`（如 `live_camera_demo.py`、`yamnet_live_demo.py`），不以 `test_` 为前缀。
