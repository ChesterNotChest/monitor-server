# 分工文档 — Web 前端（SRS + WebRTC 联调）

**接手范围**: SRS 启动与配置、WebRTC 拉流验证、前端播放器接入
**依赖**: Server 提供 `webrtc_url`（通过 `GET /api/v1/views/{id}` 获取）；不需要碰 AI 管线代码

---

## 一、上下文

当前调试阶段用 `rtmp_debug_server.js`（node-media-server）在 :1936 提供 RTMP 流，VLC 播放延迟约 2 秒。架构已为 WebRTC 低延迟播放预留了 SRS（`srs-bin/srs-setup.exe`、`srs/srs.conf`）。

目标：启动 SRS 替代 node-media-server，让前端能通过 WebRTC 拉流，延迟从 ~2s 降到 ~200ms。

整体拓扑：

```
Camera → Node(ffmpeg推RTMP) → :1935 → Server(拉流+AI推理) → RTMP推 → SRS :1936 → WebRTC → 浏览器
```

前端只需要跟 Server 的 REST API 和 SRS 的 WebRTC 端点打交道。

---

## 二、SRS 本地启动

### 安装

SRS Windows 安装包已提交到仓库：`srs-bin/srs-setup.exe`。双击安装，默认路径 `C:\Program Files\SRS\`。

### 启动（替代 rtmp_debug_server.js）

```powershell
# Terminal 1 — 用 SRS 替代 node-media-server
C:\Program Files\SRS\srs.exe -c E:\AI\monitor-server\srs\srs.conf
```

SRS 监听端口：
- `:1935` — RTMP（ffmpeg 推流入口，Server 和 Node 无需任何改动）
- `:8080` — HTTP-FLV / HTTP API / SRS 控制台
- `:8000` — WebRTC（WHEP 拉流）

验证 SRS 正常：浏览器打开 `http://127.0.0.1:8080/`，应看到 SRS 控制台。

### Server 切换

Server 启动时将 `DEBUG_WEB_STREAM` 从 `true` 改为 `false`：

```powershell
$env:DEBUG_WEB_STREAM = "false"  # 之前是 "true"
```

切换后 `build_play_urls` 走 SRS 分支，`GET /api/v1/views/{id}` 的响应中 `webrtc_url` 字段会有值。

---

## 三、联调验证

### 1. 确认 RTMP 推流正常

```bash
ffprobe rtmp://127.0.0.1:1936/view/1
# 应输出 STREAM codec_type=video + STREAM codec_type=audio
```

### 2. 确认 HTTP-FLV 可播放

浏览器或 VLC 打开：
```
http://127.0.0.1:8080/live?app=view&stream=1&port=1936
```

### 3. 确认 WebRTC 可拉流

浏览器打开 SRS 内置播放器：
```
http://127.0.0.1:8080/players/whep?app=view&stream=1
```

应看到低延迟视频画面。

### 4. 确认 API 返回正确 URL

```bash
curl http://127.0.0.1:8000/api/v1/views/1 -H "Authorization: Bearer $TOKEN"
```

响应中 `webrtc_url` 应为：
```
http://127.0.0.1:8080/rtc/v1/whep/?app=view&stream=1
```

---

## 四、前端接入

### 最小接入路径

1. `POST /api/v1/auth/login` → 获取 `access_token`
2. `POST /api/v1/views/` `{"video_id":1,"audio_id":1}` → 创建 View，得到 `rtmp_url`
3. `GET /api/v1/views/{id}` → 拿到 `webrtc_url`
4. 将 `webrtc_url` 传给 WebRTC 播放器（WHEP 协议）

### WHEP 播放器参考

SRS 的 WHEP 实现兼容标准 WebRTC。前端可用任意支持 WHEP 的播放器库。SRS 自带一个简单的 demo player：

```
http://127.0.0.1:8080/players/whep?app=view&stream={view_id}
```

正式接入时把这个页面的逻辑集成到 Web 前端即可。

### CORS 配置

如果前端从不同域名/端口访问 SRS，需要在 `srs/srs.conf` 的 `http_api` 段配置：

```nginx
http_api {
    enabled on;
    listen 8080;
    crossdomain on;  # ← 开启 CORS
}
```

---

## 五、延迟对比

| 方案 | 延迟 | 说明 |
|------|------|------|
| RTMP + VLC | ~2s | GOP cache + 播放器缓冲 |
| RTMP + SRS HTTP-FLV | ~1s | 无 GOP cache，仍有 TCP 缓冲 |
| WebRTC (WHEP) | ~200ms | UDP 直推，最低延迟 |

Web 前端正式环境应该直接走 WebRTC。RTMP/HTTP-FLV 仅用于调试。

---

## 六、启动顺序（SRS 模式）

```bash
# Terminal 0 — RTMP :1935
cd monitor-node/rtmp_server && node index.js

# Terminal 1 — SRS（替代 rtmp_debug_server.js）
C:\Program Files\SRS\srs.exe -c E:\AI\monitor-server\srs\srs.conf

# Terminal 2 — Server
cd monitor-server
$env:APP_DEBUG="false"; $env:DEBUG_WEB_STREAM="false"; $env:RTMP_DEBUG="true"; $env:YOLO_DEVICE="0"
python -m src.run

# Terminal 3 — Node
cd monitor-node
$env:RTMP_DEBUG="false"; $env:DEBUG_WSS="false"; $env:SERVER_BASE_URL="127.0.0.1"; $env:WSS_PORT="8000"; $env:RTMP_PORT="1935"
python run.py
```

注意：Terminal 2 的 `DEBUG_WEB_STREAM` 从 `true` 变为 `false`。
