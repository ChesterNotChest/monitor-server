# 模式二 Playbook：AI 标注流全链路验证

**状态**: 稳定可用（2026-07-11）  
**标注**: Person ID N + 右下角时间戳  
**编码**: NVENC GPU (p1, zerolatency), 15fps 稳推  
**测试**: 245 passed, 2 skipped  

---

## 一、拓扑

```
Camera/Mic → Node(ffmpeg dshow) → RTMP :1935 → Server(OpenCV+YOLO+标注) → RTMP :1936 → VLC
  (原始流)                                    (AI 标注流, video-only)
```

- Node 推流: `{device_name}_{device_type}_{device_id}` 如 `USB_webcam_video_1`
- Server 推标注流: `rtmp://127.0.0.1:1936/view/{view_id}`
- Audio 流独立存在（:1935 上），当前 AI 管线为 video-only

---

## 二、启动流程

### 2.1 启动顺序（严格遵守）

```bash
# ── Terminal 0: RTMP 服务器 (:1935) ──
cd E:/AI/monitor-node/rtmp_server
node index.js

# ── Terminal 1: RTMP 靶子 (:1936) ──
cd E:/AI/monitor-server/tools
node rtmp_debug_server.js

# ── Terminal 3: Node (采集+推流) ──
cd E:/AI/monitor-node
$env:RTMP_DEBUG="false"
$env:DEBUG_WSS="false"
$env:SERVER_BASE_URL="127.0.0.1"
$env:WSS_PORT="8002"
$env:RTMP_PORT="1935"
python run.py

# ── Terminal 2: Server (AI 管线) ──
cd E:/AI/monitor-server/monitor-server
Remove-Item monitor.db* -Force                    # 清 DB 避免 streaming flag 残留
$env:DEBUG_WEB_STREAM="true"
$env:YOLO_DEVICE="0"
$env:APP_DEBUG="false"
$env:PORT="8002"
python -u -m src.run
```

### 2.2 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `APP_DEBUG=false` | 必设 | 禁用 uvicorn reload，否则改代码会断 WSS |
| `PORT=8002` | 推荐 | 避开 :8000 僵尸进程 |
| `YOLO_DEVICE=0` | GPU 机器 | CPU 机器用 `cpu` |
| `DEBUG_WEB_STREAM=true` | 必设 | 推流到 :1936（而非 SRS） |

### 2.3 创建 View

```bash
cd E:/AI/monitor-server/monitor-server

# 读取密码
$PWD = (Get-Content admin_password.txt | Select-String "密码: (.+)" | % { $_.Matches.Groups[1].Value })

# 登录
$TOKEN = (Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/v1/auth/login" -Method POST `
  -ContentType "application/json" `
  -Body "{`"username`":`"admin`",`"password`":`"$PWD`"}").access_token

# 等设备就绪（心跳 30s 一次）
while (-not ((Invoke-RestMethod "http://127.0.0.1:8002/api/v1/nodes/1/videos" `
  -Headers @{Authorization="Bearer $TOKEN"}).videos.Count -gt 0)) { sleep 5 }

# 创建 View
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/v1/views/" -Method POST `
  -Headers @{Authorization="Bearer $TOKEN"} -ContentType "application/json" `
  -Body '{ "video_id": 1, "audio_id": 1 }'

# VLC 播放
vlc rtmp://127.0.0.1:1936/view/1
```

---

## 三、验证 Checklist

- [ ] 双靶子在线：`netstat -ano | findstr "1935.*LISTEN"` 和 `1936`
- [ ] Node 在线：`port :5000 LISTEN`
- [ ] Server 在线：`port :8002 LISTEN`
- [ ] 设备已注册：`GET /api/v1/nodes/1/videos` 返回 `USB webcam`
- [ ] View 创建零警告或仅 `already in use`（非阻塞）
- [ ] VLC 播放 `rtmp://127.0.0.1:1936/view/1`
- [ ] 画面有 YOLO 框 + `Person ID N` 标签
- [ ] 右下角有 `HH:MM:SS` 时间戳
- [ ] 流声明 15fps：`ffprobe -v error -show_entries stream=r_frame_rate rtmp://127.0.0.1:1936/view/1`
- [ ] obs 日志正常：`[obs] FPS=15.0 | r=0 y=16 hk=0 dr=0 ms | pipe=78 frame_age=77 ms`
- [ ] 编码器确认：日志中 `Using encoder: h264_nvenc`
- [ ] 帧删除 View 后可重建
- [ ] 重连 VLC 不出现长时间快进

---

## 四、关键设计决策

### 一笔标注（单遍绘制）
- 不改旧架构的两遍绘制（`draw_detections` + `draw_part_b_overlay`）
- 用 `Detection.label_suffix` 在 YOLO 检测上直接附加 Track ID/Face/Action/Fence
- 省去 `draw_part_b_overlay` 的 `frame.copy()`（~1ms/帧），消除两个旧 Bug

### 编码器三级回退
- `_detect_encoder()`: NVENC → h264_mf → libx264
- NVENC 参数: `-preset p1 -tune ll -b:v 2M -rc vbr -zerolatency 1 -delay 0 -g 30`

### 时钟门控 + 自适应跳帧
- 循环入口按 `_push_interval=1/FPS_TARGET` 等待整拍
- 落后超过 1 帧时重置时钟丢弃积压
- 消除 YOLO 耗时波动 + asyncio 拥堵导致的延迟累积

### video-only（音频留缺口）
- pipe:0 + RTMP 音频双输入在一个 ffmpeg 中死锁（conda & system ffmpeg 均复现）
- 两阶段方案（pipe:0 → 中间 RTMP → 最终合流）已验证可行但有缓冲延迟
- 当前暂用 video-only，音频合流待 SRS 或后续优化

---

## 五、坑点清单

### 坑 1: FrameReader 一次性失败即死
**现象**: Node 晚启动几秒 → 管线永久不可用  
**根因**: `_run_loop` 中 `FrameReader.ERROR` 直接 `break`，无重试  
**当前**: 已在 task 文档中计划修复，未实施  
**规避**: 严格按启动顺序，Node 推流就绪后再创建 View

### 坑 2: DB streaming flag 残留
**现象**: 反复创建 View 后出现 `stream already in use or unavailable` 警告  
**根因**: 未删除 `monitor.db-wal` / `monitor.db-shm` 导致旧状态复活  
**修复**: 删除所有三个文件：`Remove-Item monitor.db* -Force`

### 坑 3: uvicorn reload 导致 WSS 断开
**修复**: 设 `APP_DEBUG=false`

### 坑 4: :8000 僵尸进程
**现象**: 重启 Server 时 `port already in use`  
**规避**: 使用 `PORT=8002`

### 坑 5: DetachedInstanceError
**根因**: 后台线程引用已关闭 DB session 的 ORM 对象  
**修复**: `view_task.py` 中 `_video_name = video.name` 提前捕获

### 坑 6: Node ffmpeg 画质时间戳（drawtext）性能问题
**现象**: 加上 drawtext 后 Node 推流延迟从 20s 增长到 50s  
**当前**: 已移除 Node drawtext，Server 侧用 cv2.putText（零开销）

### 坑 7: GOP 缓存导致重连快进 + 帧率误判

**现象 A** (已修复): VLC 重连 :1936 后从旧 GOP 开始回放  
**现象 B** (2026-07-11 发现): 即便 VLC 正常，obs 显示 0ms/288ms 交替振荡，表观帧率 ~10fps  

**根因**: `node-media-server` 的 `gop_cache: true` 在 GOP 完成前不为新客户端提供数据。这对两个靶子有不同影响：

- **:1936** — VLC 重连时收到缓冲的旧 GOP → 快进回放
- **:1935** — Server FrameReader 首次连接时 30s 超时；连通后帧以 GOP 为单位批量到达 → 读取时间 0ms/288ms 交替 → 表观帧率被压缩到 ~10fps → **误导判断为"Node 性能不足"**（实际摄像头稳出 30fps）

**修复**: 两个靶子都设 `gop_cache: false`  
- `tools/rtmp_debug_server.js` — 已修（:1936）  
- `monitor-node/rtmp_server/index.js` — 2026-07-11 修（:1935）

> **关键教训**: GOP 缓存不仅影响重连体验，还会扭曲帧到达时间分布，导致 obs 数据产生系统性偏差。
> 帧率对齐问题（采集 30fps → 推流 30fps）只有在 `gop_cache: false` 后才会暴露。

### 坑 8: FPS_TARGET 与采集帧率不匹配 → 慢动作

**现象**: obs 显示稳定 FPS、r=0、无振荡，但 VLC 画面是慢动作  
**根因**: 摄像头采集 30fps，管线只取 15fps（`FPS_TARGET=15`），每两帧跳一帧 → 时间拉伸 2×  
**修复**: `FPS_TARGET` 对齐摄像头实际采集率（当前 30）  
**诊断**: `ffprobe rtmp://127.0.0.1:1935/live/...` 看源流 `r_frame_rate`，对比 Server 的 `r_frame_rate`

---

## 六、观测日志

每 5 秒打印一行，格式：

```
[obs] FPS=15.0 | r=0 y=16 hk=0 dr=0 ms | pipe=78 frame_age=77 ms
```

| 字段 | 含义 | 健康值 |
|------|------|--------|
| `FPS` | 实际循环帧率 | 13-15 |
| `r` | FrameReader 耗时 | 0ms |
| `y` | YOLO 推理耗时 | 15-32ms |
| `hk` | 帧钩子耗时（face/slowfast/fence） | <10ms |
| `dr` | 标注绘制耗时 | 0ms |
| `pipe` | 单帧管线总耗时 | <80ms |
| `frame_age` | 帧从采集到处理的延迟 | <100ms |

push FPS 单独一行：

```
[obs] push FPS: 15.0 (frames=75)
```

---

## 七、快速诊断

```bash
# 服务存活
netstat -ano | findstr "1935.*LISTEN 1936.*LISTEN 5000.*LISTEN 8002.*LISTEN"

# Node 视频流
ffprobe -v error -show_entries stream=codec_type rtmp://127.0.0.1:1935/live/USB_webcam_video_1

# AI 标注流
ffprobe -v error -show_entries stream=r_frame_rate rtmp://127.0.0.1:1936/view/1

# 列出 View
curl -s http://127.0.0.1:8002/api/v1/views/ -H "Authorization: Bearer $TOKEN"

# 查看 obs 日志
grep "\[obs\]" <server_output_file>
```
