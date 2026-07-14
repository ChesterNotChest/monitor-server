# 模式二 Playbook：AI 标注流全链路验证

**状态**: 稳定可用（2026-07-12）  
**标注**: Person ID N + Face: Chester/Stranger + Fence + 右下角时间戳  
**编码**: NVENC GPU (p1, zerolatency), 17fps 稳推  
**RTMP**: SRS 5.0 替代 node-media-server，统一 :1935  
**测试**: 250 passed, 1 skipped  
**目录假设**: monitor-server、monitor-node、monitor-web 为同级目录

### 前置清理（每次复现前执行）

多次启停会在系统中累积僵尸进程（孤儿 bash + curl 重试循环），导致 API 被反复调用、View 膨胀、Server 崩溃。

```powershell
# 杀所有残留进程（SRS 除外，如不需要重启 SRS 可保留）
Get-Process | Where-Object { $_.ProcessName -match "python|bash|curl|ffmpeg" } | Stop-Process -Force

# 清 DB
Remove-Item monitor-server\monitor.db* -Force

# 确认端口干净
netstat -ano | findstr "1935 5000 8002"
```

---

## 一、拓扑

```
Camera/Mic → Node(ffmpeg dshow) → RTMP :1935/live/ → SRS → Server(OpenCV+YOLO+标注) → RTMP :1935/view/ → VLC
  (原始流)                                                              (AI 标注流, video-only)
```

- Node 推原始流: `rtmp://127.0.0.1:1935/live/{device_name}_{device_type}_{device_id}` 如 `USB_webcam_video_1`
- Server 推标注流: `rtmp://127.0.0.1:1935/view/{view_id}`（SRS 统一端口）
- :1936 已废弃，旧 node-media-server 靶子不再需要
- Audio 流独立存在（:1935 /live/ 上），当前 AI 管线为 video-only

---

## 二、启动流程

### 2.1 启动顺序（严格遵守）

**启动顺序: SRS → Server → Node**。Node 最后启动，否则 WSS 会无限重试连 Server（预期行为，非故障）。

```bash
# ── Terminal 0: SRS (:1935) ──
# 注意：不要启动 node-media-server（会与 SRS 端口冲突）
# KEY POINT: 使用仓库的 srs/srs.conf，不用 SRS 安装目录下的出厂配置
#   (仓库配置: daemon off, 无 GOP 缓存, 端口全部对齐)
cd <monitor-server 项目根目录>
<path-to-srs>\objs\srs.exe -c srs\srs.conf
# 常见 SRS 路径:
#   "C:\Program Files (x86)\SRS\objs\srs.exe"    (Windows 默认安装)
#   ".\monitor-server\srs-bin\srs-setup.exe"  (仓库自带 installer)
# 验证: netstat -ano | findstr "1935.*LISTEN"

# ── Terminal 1: Server (AI 管线) ──
cd monitor-server                                 # 从项目根目录进入
Remove-Item monitor.db* -Force                    # 清 DB 避免 streaming flag 残留
$env:DEBUG_WEB_STREAM="true"
$env:YOLO_DEVICE="0"
$env:APP_DEBUG="false"
$env:PORT="8002"
python -u -m src.run

# ── Terminal 2: Node (采集+推流 → SRS) ──
cd ../monitor-node                               # 从 monitor-server 根目录切到同级 monitor-node
$env:RTMP_DEBUG="false"
$env:DEBUG_WSS="false"
$env:SERVER_BASE_URL="127.0.0.1"
$env:WSS_PORT="8002"
$env:RTMP_PORT="1935"
python run.py
# 注意: Node 的 WSS 会持续重试直到 Server 上线，启动时大量 WSS connection error 日志是正常的
```

### 2.2 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `APP_DEBUG=false` | 必设 | 禁用 uvicorn reload，否则改代码会断 WSS |
| `PORT=8002` | 推荐 | 避开 :8000 僵尸进程 |
| `YOLO_DEVICE=0` | GPU 机器 | CPU 机器用 `cpu` |
| `DEBUG_WEB_STREAM=true` | 必设 | 推流到 :1935 SRS `/view/` 路径 |
| `RTMP_PORT=1935` | 默认 | 与 SRS listen 端口一致，`.env` 中定义 |

### 2.2.1 API 路径规则

wwh 合并后路由路径已尽量统一，但各 router 定义仍有差异。**错用路径会触发 307 重定向 → Authorization header 丢失 → 401**。

```
路由 path="/"       → URL 带尾斜杠:    /api/v1/fences/  /api/v1/views/
路由 path=""        → URL 不带尾斜杠:   /api/v1/persons  /api/v1/events
路由 path="/{id}"   → URL 按原样:       /api/v1/views/1  /api/v1/fences/1/
```

| 端点 | 正确 URL |
|------|---------|
| 登录 | `POST /api/v1/auth/login/` |
| 创建设备 | `POST /api/v1/views/` |
| 删除设备 | `DELETE /api/v1/views/{id}` |
| 围栏 CRUD | 均带 `/`：`GET/POST /api/v1/fences/`、`PUT/DELETE /api/v1/fences/{id}/` |
| 人员 CRUD | `GET/POST /api/v1/persons`、`POST /api/v1/persons/{id}/avatar` |
| 事件 | `GET /api/v1/events` |

### 2.3 创建 View

```bash
cd monitor-server                                 # 从项目根目录进入

# 读取密码（与 seed_admin() 同源：.env 中 ADMIN_DEFAULT_PASSWORD）
$PWD = ((Get-Content .env | Select-String 'ADMIN_DEFAULT_PASSWORD=(.+)').Matches.Groups[1].Value).Trim()

# 登录
$TOKEN = (Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/v1/auth/login/" -Method POST `
  -ContentType "application/json" `
  -Body "{`"username`":`"admin`",`"password`":`"$PWD`"}").access_token

# 等设备就绪（心跳 30s 一次）
while (-not ((Invoke-RestMethod "http://127.0.0.1:8002/api/v1/nodes/1/videos" `
  -Headers @{Authorization="Bearer $TOKEN"}).videos.Count -gt 0)) { sleep 5 }

# 创建 View（返回的 rtmp_url 即为 VLC 播放地址）
$VIEW = Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/v1/views/" -Method POST `
  -Headers @{Authorization="Bearer $TOKEN"} -ContentType "application/json" `
  -Body '{ "video_id": 1, "audio_id": 1 }'

# VLC 播放 AI 标注流
vlc $VIEW.rtmp_url
# 或手动: vlc rtmp://127.0.0.1:1935/view/1
```

---

## 三、验证 Checklist

- [ ] SRS 在线：`netstat -ano | findstr "1935.*LISTEN"`（单端口，无 :1936）
- [ ] Node 在线：`port :5000 LISTEN`
- [ ] Server 在线：`port :8002 LISTEN`
- [ ] 设备已注册：`GET /api/v1/nodes/1/videos` 返回 `USB webcam`
- [ ] 原始流可用：`ffprobe rtmp://127.0.0.1:1935/live/USB_webcam_video_1` 返回 `h264, 30fps`
- [ ] View 创建零警告或仅 `already in use`（非阻塞）
- [ ] VLC 播放 `rtmp://127.0.0.1:1935/view/1`（注意: `/view/` 而非 `/live/`）
- [ ] 画面有 YOLO 框 + `Person ID N` 标签 + `Face: Stranger/Chester`
- [ ] 右下角有 `HH:MM:SS` 时间戳（Node drawtext）
- [ ] 流声明 17fps：`ffprobe -v error -show_entries stream=r_frame_rate rtmp://127.0.0.1:1935/view/1`
- [ ] obs 日志正常：`[obs] FPS=17.0 | r=0 y=16 hk=0 dr=0 ms | pipe=<50 age=<50ms`
- [ ] 编码器确认：日志中 `Using encoder: h264_nvenc`
- [ ] 帧删除 View 后可重建
- [ ] Server 重启后自动恢复已有 View 管线（日志：`Auto-recovered N existing view pipeline(s)`）
- [ ] 重连 VLC 不出现长时间快进

---

## 四、关键设计决策

### SRS 单端口统一 ✅ (2026-07-12)
- SRS 5.0 替代 node-media-server，所有流走 `:1935`
- `/live/` = 原始流（Node 推入），`/view/` = AI 标注流（Server 推出）
- :1936 废弃，`DEBUG_RTMP_PORT` 从配置读取（`settings.RTMP_PORT`）

### View 管线自动恢复 ✅ (2026-07-12)
- Server 重启后自动遍历 DB 中所有 View，恢复 AI 管线
- `app.py` startup 事件中执行，`start_pipeline` 已有幂等保护
- 日志验证：`Auto-recovered N existing view pipeline(s)`

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

### 坑 1: FrameReader 一次性失败即死 ✅ (2026-07-11)
**现象**: Node 晚启动几秒 → 管线永久不可用  
**根因**: `_run_loop` 中 `FrameReader.ERROR` 直接 `break`，无重试  
**修复**: 指数退避重试 2s→60s，最多 10 次。首次 `open()` 失败不再阻止启动

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
**当前**: Node drawtext 始终在跑（`ffmpeg_dshow.py`），延迟问题已通过 nobuffer+4M+GOP false+17fps 组合缓解，obs age=75ms 不影响

### 坑 7: GOP 缓存导致重连快进 + 帧率误判 ✅ (2026-07-11)

**现象 A**: VLC 重连后从旧 GOP 开始回放  
**现象 B**: obs 显示 0ms/288ms 交替振荡，表观帧率 ~10fps  

**根因**: node-media-server 的 `gop_cache: true` 在 GOP 完成前不为新客户端提供数据，扭曲帧到达时间分布  

**修复**: node-media-server 设 `gop_cache: false`（当前已切 SRS，该问题不再适用）

> **关键教训**: GOP 缓存不仅影响重连体验，还会扭曲帧到达时间分布，导致 obs 数据产生系统性偏差。

### 坑 8: FPS_TARGET 与采集帧率不匹配 → 慢动作 ✅ (2026-07-11)

**现象**: obs 显示稳定 FPS、r=0、无振荡，但 VLC 画面是慢动作  
**根因**: 摄像头采集 30fps，管线只取 15fps（`FPS_TARGET=15`），每两帧跳一帧 → 时间拉伸 2×  
**修复**: `FPS_TARGET=17` 对齐 Node 采集帧率（Node: `-framerate 17`）  
**诊断**: `ffprobe rtmp://127.0.0.1:1935/live/...` 看源流 `r_frame_rate`，对比 Server 的 `r_frame_rate`

---

### 坑 9: conda+pip 混装 → PyTorch CUDA 失效

**现象**: `torch.cuda.is_available()` 返回 `False`，Server 启动时报 `torch_cuda.dll` 加载失败  
**根因**: `conda env update --prune` 装 TF 时覆盖了 PyTorch 需要的 CUDA/cuDNN DLL。  
         pip 装的 PyTorch cu124 wheel 自带 CUDA 库但不含 cuDNN；conda 的 cuDNN 被 `--prune` 删除。  
**修复**:
```bash
# 重装 CUDA 版 PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
# 补回 cuDNN（如缺失）
conda install -n monitor-server -c conda-forge cudnn --yes
```
**诊断**: `ls $CONDA_PREFIX/Library/bin/cudnn*` 应有输出（或 `ls %CONDA_PREFIX%\Library\bin\cudnn*`）。
**预防**: `environment.yml` 已加 `conda-forge::cudnn`，`--prune` 不会再删。

> **教训**: TF+PyTorch 双框架是结构性冲突，conda 无法同时满足两者的 CUDA 版本需求。
> 策略是让 PyTorch 赢（项目主力是 YOLO），TF 顺从现有 CUDA 版本。

---

## 六、观测日志

每 5 秒打印一行，格式：

```
[obs] FPS=15.0 | r=0 y=16 hk=0 dr=0 ms | pipe=78 frame_age=77 ms
```

| 字段 | 含义 | 健康值 |
|------|------|--------|
| `FPS` | 实际循环帧率 | 15-17（目标 17） |
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
# 服务存活（SRS 单端口，无 :1936）
netstat -ano | findstr "1935.*LISTEN 5000.*LISTEN 8002.*LISTEN"

# 原始流（Node → SRS）
ffprobe -v error -show_entries stream=codec_type rtmp://127.0.0.1:1935/live/USB_webcam_video_1

# AI 标注流（Server → SRS /view/）
ffprobe -v error -show_entries stream=r_frame_rate rtmp://127.0.0.1:1935/view/1

# 列出 View
curl -s http://127.0.0.1:8002/api/v1/views/ -H "Authorization: Bearer $TOKEN"

# 查看 obs 日志
grep "\[obs\]" <server_output_file>
```

---

## 八、日报系统

### 配置

在 `.env` 中设置（可选，不设置则仅统计层可用）：

```env
# DeepSeek API Key（申请地址: https://platform.deepseek.com）
DEEPSEEK_API_KEY=sk-xxxxxxxx
# 模型选择（推荐 deepseek-v4-flash，性价比最高）
DEEPSEEK_REPORT_MODEL=deepseek-v4-flash
```

安装依赖后重启 Server：

```bash
pip install apscheduler>=3.10.0
python run.py
```

### 定时规则

| 时间 | 动作 |
|------|------|
| 每日 17:00 CST | 自动生成当日日报（00:00~17:00），含统计层 + AI 洞察（若配置 Key） |
| 每日 00:05 CST | 补充前一日余量（17:00~23:59），覆盖为全天数据，重新生成 AI 洞察 |
| 服务启动时 | 检查当日日报是否缺失，缺失则补生成 |

所有时间均为北京时间 (UTC+8)。

### API 端点

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8002/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 获取持久化日报（新格式: stats + insights）
curl -s "http://127.0.0.1:8002/api/v1/reports/daily/persisted/?date=2026-07-14" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool | head -40

# 手动即时生成（00:00~now CST）
curl -s -X POST "http://127.0.0.1:8002/api/v1/reports/daily/generate-now/" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool | head -20

# 查看/配置 API Key
curl -s "http://127.0.0.1:8002/api/v1/reports/settings/" \
  -H "Authorization: Bearer $TOKEN"

curl -s -X PUT "http://127.0.0.1:8002/api/v1/reports/settings/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"sk-your-key","model":"deepseek-v4-flash"}'

# 旧版日报端点（向后兼容）
curl -s "http://127.0.0.1:8002/api/v1/reports/daily/?date=2026-07-14" \
  -H "Authorization: Bearer $TOKEN"
```

### 前端入口

- 日报页面: `http://localhost:5173/report/2026-07-14`
- 「立即生成当天日报」按钮 → POST `/daily/generate-now/`
- 「API Key」按钮 → 齿轮图标弹窗配置
- 日期选择器 → 切换历史日报
- 页面底部 → 显示"北京时间 (UTC+8)"和"下次自动生成时间"
