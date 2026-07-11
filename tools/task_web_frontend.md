# 任务三 — Web 前端（SRS 拉流联调）

**接手范围**: `E:/AI/monitor-web` 前端代码 + SRS 本地启动  
**依赖**: Server 提供带标注的流 URL（`GET /api/v1/views/{id}`→ `flv_url` / `rtmp_url`）；不需要碰 AI 管线代码  
**测试用流**: 使用原始合流（`ffmpeg_manager.start_merge` 直接推送 RTMP），不依赖 AI 标注就绪

---

## 一、当前状态（已就绪，不需要重做）

前端已大规模接入，以下均为**已完成**工作：

- **CRUD 全部封装** — `src/api/client.ts` 覆盖全部 Server REST 端点：auth、alerts、alert-groups、dashboard、nodes、devices、detection types、exceptions、fences、logs、persons（含头像上传 `uploadPersonAvatar`）、users、events、replay、views
- **LiveMonitor 页面已用 flv.js 播放** — `src/pages/LiveMonitor.tsx:50-54` 读取 `view.flv_url`，通过 `flv.js.createPlayer({ type: 'flv', url: view.flv_url, isLive: true })` 创建播放器并 attach 到 `<video>` 元素。支持 loading / error / retry 三态
- **路由已注册** — `/view/:cameraId` → LiveMonitor，`/view/:viewId/edit` → FenceEditor
- **`ViewResponse` 类型**已定义 `flv_url`, `rtmp_url`, `webrtc_url` 字段

**当前缺失的只有一步**：`flv_url` 的值。在当前的 `DEBUG_WEB_STREAM=true` 模式下，Server `build_play_urls()` 返回 `flv_url: null`，前端拿到 null 后显示空状态。**需要切换到 SRS 模式让 `flv_url` 有值。**

---

## 二、SRS 启动（替代 rtmp_debug_server.js）

SRS 安装包已提交：`srs-bin/srs-setup.exe`。安装后默认路径 `C:\Program Files\SRS\`。

```powershell
# Terminal 1 — 用 SRS 替代 rtmp_debug_server.js
C:\Program Files\SRS\srs.exe -c E:\AI\monitor-server\srs\srs.conf
```

SRS 监听：
- `:1935` — RTMP 推流入口（Server ffmpeg 推流目标）
- `:8080` — HTTP-FLV / HTTP API / SRS 控制台
- `:8000` — WebRTC WHEP 拉流

### Server 切换

```powershell
$env:DEBUG_WEB_STREAM = "false"  # 必须是 "false"
```

切换后 `build_play_urls()` 返回完整 URL：

```json
{
  "rtmp_url":   "rtmp://127.0.0.1:1935/view/1",
  "flv_url":    "http://127.0.0.1:8080/view/1.flv",
  "webrtc_url": "http://127.0.0.1:8080/rtc/v1/whep/?app=view&stream=1"
}
```

---

## 三、联调步骤

### Step 1 — 启动全链路

```bash
T0: node monitor-node/rtmp_server/index.js                    # RTMP :1935
T1: C:\Program Files\SRS\srs.exe -c srs\srs.conf             # SRS :1935/:8080
T2: $env:DEBUG_WEB_STREAM="false"; python -m src.run          # Server :8000
T3: python monitor-node/run.py                                 # Node  :5000

# 创建 View
curl -X POST http://127.0.0.1:8000/api/v1/views/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"video_id":1,"audio_id":1}'
```

### Step 2 — 验证 flv_url

```bash
curl http://127.0.0.1:8000/api/v1/views/1 -H "Authorization: Bearer $TOKEN"
# 检查 flv_url: "http://127.0.0.1:8080/view/1.flv"

# 用 ffprobe 验证可访问
ffprobe http://127.0.0.1:8080/view/1.flv
```

### Step 3 — 前端 flv.js 播放

前端启动后访问 `http://localhost:5173/view/1`，LiveMonitor 自动用 `flv_url` 创建 flv.js 播放器。预期：视频正常渲染，左上角 LIVE 标签显示。若加载失败显示错误 + 重试按钮。

### Step 4 — WebRTC（后续）

浏览器打开 `http://127.0.0.1:8080/players/whep?app=view&stream=1` 验证低延迟。正式接入则用 `view.webrtc_url` 传给 WebRTC 播放器。

---

## 四、需检查的问题

1. **删除 View 后 flv_url 残留** — `debug_data.py` 有 60 秒自动恢复录制文件的循环逻辑，**这个没修好**。若影响调试，设 `DEBUG_FLV_TRANSMIT=false` 关闭。

2. **删除 View 后前端状态** — LiveMonitor 删除 View 后是否跳转回 `/main`？当前可能停留在空状态页。

3. **CORS** — SRS HTTP :8080 需 `crossdomain on;`，否则前端 localhost:5173 访问被拦截。

4. **Node RTMP :1935 的 node-media-server 和 SRS 都监听 :1935** — 冲突。SRS 启动后 RTMP :1935 由 SRS 提供，不再需要 `rtmp_server/index.js` 的 Terminal 0。
