# 任务三 — Web 前端通讯对齐

**接手范围**: `E:/AI/monitor-web`  
**依赖**: Server API + SRS 流媒体（本地启动即可，见 §二）  
**目标**: 完成浏览器端全链路——登录→设备查看→创建 View→flv.js 播放→告警面板→删除 View

---

## 一、已完成（无需返工）

`src/api/client.ts` 封装了全部 Server REST 端点，覆盖 auth / alerts / dashboard / nodes / devices / exceptions / fences / logs / persons（含头像上传）/ users / events / replay / views。14 个页面路由已注册。

**关键文件**：

| 文件 | 作用 | 状态 |
|------|------|------|
| `src/api/client.ts` | 全部 API 封装（~500 行） | ✅ |
| `src/pages/LiveMonitor.tsx` | flv.js 播放 + 告警侧栏 | ⚠️ 未端到端验证 |
| `src/pages/MainDashboard.tsx` | KPI 统计 + View 列表 + 快捷入口 | ✅ 已验证 |
| `src/pages/DeviceInfo.tsx` | Node/设备树展示 | ✅ 已验证 |
| `src/pages/FenceEditor.tsx` | 电子围栏编辑器 | ⚠️ 需联调验证 |
| `src/context/AlertContext.tsx` | 告警轮询 + 全局状态 | ⚠️ 需端到端验证 |

---

## 二、SRS 环境（一次性）

SRS v5.0 安装包已更新到 `srs-bin/srs-setup.exe`（14.8MB）。安装到 `C:\Program Files\SRS\`。

启动（替代 `rtmp_debug_server.js`，**同时替代 `rtmp_server/index.js` 的 :1935**）：

```powershell
C:\Program Files\SRS\srs.exe -c E:\AI\monitor-server\srs\srs.conf
```

SRS 监听 `:1935`（RTMP 推拉）+ `:8080`（HTTP-FLV）+ `:8000`（WebRTC）。配置文件 `srs/srs.conf` 已启用 `http_remux`（RTMP → FLV 自动转换）和 `rtc_server`（WebRTC）。

Server 侧配合切换：

```powershell
$env:DEBUG_WEB_STREAM = "false"
```

此后 `GET /api/v1/views/{id}` 返回：

```json
{
  "rtmp_url":   "rtmp://127.0.0.1:1935/view/1",
  "flv_url":    "http://127.0.0.1:8080/view/1.flv",
  "webrtc_url": "http://127.0.0.1:8080/rtc/v1/whep/?app=view&stream=1"
}
```

---

## 三、对齐清单（逐项验证）

### 3.1 View 创建 → 播放 → 删除 全生命周期

1. **创建 View**：`POST /views` `{video_id: 1, audio_id: 1}`，约 8 秒返回。前端 `createView()` 已封装。
2. **轮询/刷新 View 列表**：`MainDashboard` 已调用 `fetchViews()`，验证新建 View 出现在列表中。
3. **进入 LiveMonitor**：点击 View → 路由到 `/view/{id}`。`LiveMonitor` 调用 `fetchViewById(id)` → 取 `view.flv_url` → `flv.js.createPlayer()` → `<video>` 播放。
4. **删除 View**：`DELETE /views/{id}` → 前端 `deleteView(id)` → 是否自动返回 `/main`？当前可能停留在空状态页。

### 3.2 LiveMonitor 直播播放（WebRTC，当前未实现）

**架构纠正**：直播用 WebRTC（`webrtc_url`，延迟 ~200ms），回放用 FLV（`flv_url`，录播文件）。

当前 `LiveMonitor.tsx` 错误地用了 `flv_url` + flv.js 做直播——需要改为 WHEP WebRTC 播放器：

1. 取 `view.webrtc_url`（`http://127.0.0.1:8080/rtc/v1/whep/?app=view&stream=1`）
2. `new RTCPeerConnection()` → `addTransceiver('video')` + `addTransceiver('audio')`
3. WHEP 握手：`POST webrtc_url` 拿 SDP offer → `setRemoteDescription` → 生成 answer → `PATCH webrtc_url` 回传
4. 收到 track → attach 到 `<video>` 元素

SRS 内置 WHEP demo（参考实现）：`http://127.0.0.1:8080/players/whep?app=view&stream=1`

**LiveMonitor 改动**：删掉 flv.js 引用，替换为 WHEP 播放器。`flv_url` 和 flv.js 相关代码（含 error/retry 逻辑）移到 EventReplay 备用。

### 3.3 EventReplay 回放播放（FLV，已实现）

`EventReplay.tsx` 用 flv.js 播放录制文件——架构正确。已实现进度条拖拽、播放/暂停、时间轴、告警处理（标记已处理/误报）、自动跳转返回。需验证：

- `GET /recordings/{id}/stream` 返回 FLV 流（当前 `debug_data.py` 提供测试文件）
- flv.js 正常加载、播放、seek
- 进度条拖拽定位准确
- 告警处理后 1.5s 自动跳转回上页

### 3.4 告警面板

`LiveMonitor` 右侧告警面板过滤 `alerts.filter(a => a.view_id === viewId)`，显示告警 ID、时间戳、"查看回放"按钮 → 路由到 `/replay/{alertId}`。

需要验证：AI 管线检测到异常后 `AlertContext` 是否在轮询中捕获到新告警。

### 3.4 创建 View 流程（MainDashboard 缺入口）

**DeviceInfo 保持不动**——它是设备状态看板，不是 View 创建页。

创建 View 的入口应该在 **MainDashboard**——那里已经有 View 列表网格，缺一个"创建监控视图"按钮。API 层全部就绪（`fetchNodeVideos`、`fetchNodeAudios`、`createView`），只缺 UI：

1. MainDashboard 的 View 网格上方或首个位置加"＋ 创建监控视图"按钮
2. 点击 → 进入一个专门的创建 View 页面
3. 页面加载 Node 下的 video 设备列表 + audio 设备列表
4. 用户各选一个 → 点击"创建" → `createView({video_id, audio_id})` → 成功后跳转 `/view/{id}`
5. `createView` 约 8 秒返回（含等待 Node 推流），需要 loading 态
6. 设备列表每条显示名称和 `streaming` 状态。已在推流的设备标"使用中"。

### 3.5 FenceEditor 围栏编辑器（视频层缺失）

`FenceEditor` 是独立路由页（`/view/:viewId/edit`），从 LiveMonitor 的"编辑电子围栏"按钮跳转过来。**架构正确**——同一个 View 的直播视频，不同的交互模式。

当前状态：
- ✅ 右侧面板：围栏列表 + 新建表单 + 删除——CRUD 已通
- ❌ 左侧面板：只有 Camera 占位图标——**缺少视频播放器**

需要补齐：
1. **嵌入 WebRTC 播放器**（与 LiveMonitor 共用的同一套逻辑），实时显示该 View 监控画面
2. **视频上方叠加 `<canvas>`**，已有围栏以半透明多边形展示
3. **鼠标交互**：点击新增顶点、拖拽移动顶点、双击删除
4. 保存时 canvas 坐标换算为视频分辨率坐标 → `createFence` / `updateFence`

### 3.6 其他页面对齐状态

| 页面 | 路由 | 状态 |
|------|------|------|
| MainDashboard | `/main` | ✅ 已验证 |
| LiveMonitor | `/view/:cameraId` | ❌ **需重构**：flv.js → WebRTC WHEP |
| EventReplay | `/replay/:alertId` | ✅ flv.js 回放已实现，待 SRS 验证 |
| MainDashboard | `/main` | ⚠️ 缺"创建 View"入口（View 网格 + 设备选择弹窗） |
| DeviceInfo | `/equipment` | ✅ 设备状态看板，不做 View 创建 |
| FenceEditor | `/view/:viewId/edit` | ❌ 左侧面板缺 WebRTC 播放器 + canvas 围栏编辑 |
| ExceptionSettings | `/exception-settings` | ✅ |
| WeeklyReportDetail | `/weekly-report/:weekNum` | ✅ |
| EventStats | `/event-stats` | ✅ |

---

## 四、已知问题

1. **SRS 安装**：`srs-bin/srs-setup.exe` 是 v5.0-r0 Windows 安装包（14.8MB），需双击安装到 `C:\Program Files\SRS\`。之前仓库里那个 4.6MB 版本已损坏，已替换。

2. **端口合并**：SRS 替代了两个老服务——`:1935` 不再需要 `rtmp_server/index.js`，`:1936` 不再需要 `rtmp_debug_server.js`。Node 推流 → SRS :1935，Server AI 推流 → SRS :1935，Server 拉流 ← SRS :1935，前端拉流 ← SRS :8080。**测试时只启动 SRS + Server + Node 三个进程。**

3. **`debug_data.py` 60 秒恢复循环**：`DEBUG_FLV_TRANSMIT=true` 时自动创建测试数据链路，告警处理后录制文件被删，60 秒后自动恢复。**这个循环没修好**——前端测试期间设 `DEBUG_FLV_TRANSMIT=false` 关闭。

4. **CORS**：SRS HTTP :8080 需 `crossdomain on;`，否则前端 localhost:5173 → SRS :8080 被浏览器拦截。

5. **`flv_url` 为 null 的前端降级**：`LiveMonitor` 在 `flv_url` 为 null 时显示空状态（Camera 图标 + "视图 N"）。SRS 模式下应有值，但如果 SRS 挂了、端口冲突、或 `DEBUG_WEB_STREAM` 忘切，前端应给明确提示而非静默空状态。

6. **`rtmp_url` vs `flv_url` 双重播放链路**：当前 `LiveMonitor` 只用 `flv_url`（HTTP-FLV）。如果 SRS 不可用但用户想看视频，`rtmp_url` 是备选——但浏览器不支持 RTMP，需提示用户"请用 VLC 打开 rtmp_url"。这个降级逻辑前端还没做。

---

## 五、启动顺序（SRS 模式）

```
T0: C:\Program Files\SRS\srs.exe -c E:\AI\monitor-server\srs\srs.conf
T1: $env:DEBUG_WEB_STREAM="false"; $env:YOLO_DEVICE="0"; python -m src.run
T2: python monitor-node/run.py
```

三个进程。Node 推流到 :1935，Server 从 :1935 拉流+AI 推理后推到 :1935。前端从 :8080 拉 HTTP-FLV。

---

## 六、手测 Checklist（按顺序，每步必须通过才能往下）

### 6.1 环境准备

- [ ] **SRS 已安装**：`C:\Program Files\SRS\srs.exe` 存在
- [ ] **SRS 启动正常**：`srs.exe -c srs/srs.conf` 后访问 `http://127.0.0.1:8080/` 看到 SRS 控制台
- [ ] **Server 切了 SRS 模式**：启动时 `$env:DEBUG_WEB_STREAM = "false"`
- [ ] **端口无冲突**：`:1935` 只有 SRS 一个进程在监听，没有残留的 `rtmp_server/index.js`

### 6.2 Server API 验证（curl / Postman）

- [ ] `POST /api/v1/auth/login` 返回 `access_token`（admin 密码见 `admin_password.txt`）
- [ ] `GET /api/v1/nodes/` 返回在线 Node 列表
- [ ] `GET /api/v1/nodes/1/videos` 返回 video 设备列表（含 `id`、`name`、`streaming`）
- [ ] `GET /api/v1/nodes/1/audios` 返回 audio 设备列表
- [ ] `POST /api/v1/views/ {"video_id":1,"audio_id":1}` 返回 View，约 8 秒
  - **期望**：`rtmp_url`、`flv_url`、`webrtc_url` 三个字段都有值，不是 null
  - **如果 null**：检查 `DEBUG_WEB_STREAM=false` 是否生效，检查 SRS 是否在跑
- [ ] `GET /api/v1/views/{id}` 返回同上，三个 URL 完整

### 6.3 流验证（ffprobe / VLC）

- [ ] `ffprobe rtmp://127.0.0.1:1935/view/1` 返回 `STREAM codec_type=video` + `codec_type=audio`
- [ ] VLC 打开 `rtmp://127.0.0.1:1935/view/1`，画面正常播放
- [ ] `ffprobe http://127.0.0.1:8080/view/1.flv` 返回 video + audio 流（验证 HTTP-FLV 可用）
- [ ] 浏览器打开 `http://127.0.0.1:8080/players/whep?app=view&stream=1`，看到低延迟画面（验证 WebRTC 可用）

### 6.4 前端页面（浏览器 localhost:5173）

- [ ] **登录页** `/login`：输入 admin / 密码，登录成功跳转 `/main`
- [ ] **主面板** `/main`：KPI 统计正常，View 列表显示已创建的 View，点击进入 LiveMonitor
- [ ] **LiveMonitor** `/view/1`：WebRTC 视频正常播放，延迟明显低于 VLC RTMP。右侧告警面板显示"当前视图无未处理告警"（空状态正常）
- [ ] **FenceEditor** `/view/1/edit`：左侧显示同一路实时视频，右侧围栏列表可新建/删除。Canvas 可绘制多边形并保存
- [ ] **EventReplay** `/replay/1`：flv.js 加载录制文件，进度条可拖拽，播放/暂停正常。标记"已处理"后 1.5s 跳转回上页
- [ ] **设备信息** `/equipment`：展开 Node 显示在线状态、最后上线时间（不做 View 创建）
- [ ] **删除 View**：LiveMonitor 或 MainDashboard 删除 View 后，返回 `/main`，View 列表更新
- [ ] **删除 View 后流停止**：`ffprobe rtmp://127.0.0.1:1935/view/1` 返回连接失败（流已断开）

### 6.5 CORS 检查

- [ ] 前端 localhost:5173 访问 SRS localhost:8080 不报 CORS 错误。如果报错，`srs/srs.conf` 的 `http_api` 加 `crossdomain on;` 并重启 SRS
