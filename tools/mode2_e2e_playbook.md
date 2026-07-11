# 模式二联调实录：从零到标注流的全链路

**服务对象**: 后续接手联调的开发者、Web 前端流对齐  
**最后更新**: 2026-07-11  
**当前状态**: 合流可看 (:1936)，YOLO 模型加载成功，待 FrameReader 拉流 & 标注验证

---

## 一、拓扑

```
Camera/Mic → Node(ffmpeg推流) → RTMP :1935 → Server(拉流+AI推理) → RTMP :1936 → VLC/OBS/Web
(原始流)                                    (标注流)
```

- Node 推流命名: `{device_name}_{device_type}_{device_id}` 如 `USB_webcam_video_1`
- Server 推标注流: `rtmp://127.0.0.1:1936/view/{view_id}`

---

## 二、线性启动流程

### 2.1 启动顺序（必须严格遵守）

| 顺序 | 终端 | 命令 | 端口 |
|---|---|---|---|
| 0 | RTMP 服务器 | `node monitor-node/rtmp_server/index.js` | :1935 |
| 1 | RTMP 靶子 | `node monitor-server/tools/rtmp_debug_server.js` | :1936 |
| 2 | Server | `cd monitor-server && APP_DEBUG=false DEBUG_WEB_STREAM=true RTMP_DEBUG=true python -m src.run` | :8000 |
| 3 | Node | `cd monitor-node && RTMP_DEBUG=false DEBUG_WSS=false SERVER_BASE_URL=127.0.0.1 WSS_PORT=8000 RTMP_PORT=1935 python run.py` | :5000 |

**关键**: 必须用 `APP_DEBUG=false` 禁用 uvicorn reload，否则改代码时 Server 重启会导致 WSS 断开 → Node 推流中断。

### 2.2 API 验证序列

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<从 admin_password.txt 读取>"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. 等设备同步（Node 心跳 30s 一次）
until curl -s "http://127.0.0.1:8000/api/v1/nodes/1/videos" \
  -H "Authorization: Bearer $TOKEN" | grep -q "USB"; do sleep 5; done

# 3. 创建 View（触发推流 + AI 管线）
curl -s -X POST http://127.0.0.1:8000/api/v1/views/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":1,"audio_id":1}'

# 4. VLC 播放标注流
vlc rtmp://127.0.0.1:1936/view/1
```

---

## 三、坑点清单

### 坑 1: Node device_map 初始化时机

**现象**: Server 发 UPDATE_STREAM 后 Node 不推流，日志显示 `unknown device_id`

**根因**: Node 的 `server_device_map`（device_id ↔ device_name 映射）只在 WSS 认证时从 Server 的 ConnectResponse 填充。首次运行时，DB 中无设备，认证响应 `videos=0, audios=0`，映射为空。后续心跳虽同步了设备到 DB，但 Node 侧映射永不更新。

**修复**: 
- Server: 心跳处理后推送 `{"type": "device_map", "videos": [...], "audios": [...]}` 回 Node
- Node: `CommandHandler.dispatch()` 处理 `type == "device_map"` 更新映射表

**相关文件**: `node_handler.py`, `command_handler.py`

---

### 坑 2: 心跳只发已启用设备

**现象**: 模式二下 Server 始终看不到 Node 的设备列表

**根因**: Node 心跳只发送 `device_registry`（已启用/正在推流的设备），模式二下注册表为空。Server 永远不知道 Node 有哪些设备可用。

**修复**: 心跳合并 `device_registry` + `get_cached_devices()`（所有检测到的设备）

**相关文件**: `monitor-node/network/wss_client.py` `_heartbeat_loop()`

---

### 坑 3: create_view 阻塞事件循环

**现象**: POST /views 超时（30s+），WSS 心跳断开，Server 无响应

**根因**: 三处串行阻塞：
1. `cv2.VideoCapture(url)` 默认 30s FFmpeg 超时 — 帧读取器打开 RTMP 流时阻塞事件循环
2. `wait_for_streams()` 对每个 RTMP URL 做 ffprobe 探测，默认 30s timeout — 中文设备名导致 ffprobe URL 解析失败
3. `time.sleep(3)` 持有 DB 事务期间阻塞线程 — WSS 心跳写 DB 触发 `database is locked`

**修复**:
- FrameReader: 设 `OPENCV_FFMPEG_CAPTURE_OPTIONS=timeout;5000000`（5s），用 `cv2.CAP_FFMPEG` 后端
- Merge: `wait_for_inputs=False` 跳过预检，让 FFmpeg 自己处理重连
- DB: `db.commit()` 移到 `time.sleep()` 之前，释放事务锁
- SQLite: 启用 WAL 模式 + 5s busy_timeout

**相关文件**: `vision_frame_reader.py`, `view_task.py`, `extensions.py`

---

### 坑 4: uvicorn reload 导致 WSS 断开

**现象**: 启动后 Node 的 WSS 每 1-2 分钟断开重连

**根因**: `src.run` 默认 `reload=settings.DEBUG`（DEBUG 默认 True）。编辑任何源码文件触发 reload → 旧进程被杀 → WSS 连接断开。

**修复**: 联调时设 `APP_DEBUG=false`

---

### 坑 5: 流就绪与管线启动的竞态

**现象**: merge 和 pipeline 报告 "Raw stream(s) unavailable" / "FrameReader timed out"

**根因**: `check_and_start_stream` 发送 UPDATE_STREAM 后立即返回，但 Node 需要 ~5s 启动 ffmpeg 并建立 RTMP 连接。`start_merge` 和 `start_pipeline` 在流就绪前就开始检查。

**当前缓解**: `time.sleep(5)` 在 db.commit 之后等待。**理想方案**: FrameReader 带重试循环，或 pipeline 启动与 View 创建解耦（WebSocket 推送流就绪事件后再启动管线）。

---

### 坑 6: YOLO CUDA/cuDNN DLL 缺失

**现象**: Server 进程崩溃，日志 `Could not locate cudnn_ops64_9.dll`

**根因**: Ultralytics YOLO 默认尝试 CUDA 后端，Windows 环境缺少 cuDNN DLL

**修复**: `config.py` 新增 `YOLO_DEVICE: str = "cpu"`，`detector.py` 中 `self._model.to(settings.YOLO_DEVICE)` 强制 CPU 推理。GPU 机器上改环境变量 `YOLO_DEVICE=0` 即可切回。

---

### 坑 7: Node 流 URL 的 device_id 错位

**现象**: Node 推流到 `USB_webcam_video_0`，但 Server 期望 `USB_webcam_video_1`

**根因**: Node 的 `_on_auth_restart_streams` 在认证后立即重启流。若此时 server_device_map 为空（设备尚未同步），URL 中的 device_id 用 0 占位。即使后续 device_map 更新，流已在推，不会自动修正。

**规避**: 确保首次心跳完成（device_map 已更新）后再创建 View。

---

### 坑 8: conda Library/bin 不在 PATH → cuDNN 加载崩溃

**现象**: Server 进程在 create_view 时崩溃，日志 `Could not locate cudnn_ops64_9.dll`

**根因**: conda 环境通过 `cudnn`/`libcudnn` 包安装了 cuDNN DLL（位于 `Library/bin/`），但直接运行 `python.exe`（未 `conda activate`）时该目录不在 PATH 中。Windows 的 DLL 搜索依赖 PATH，当 TensorFlow/YAMNet 尝试加载 CUDA runtime 时，cudart 找到了但 cuDNN 找不到 → 进程硬崩溃（非 Python 异常）。

**修复**:
- 在 `src/run.py` 最开头（一切 import 之前）将 `sys.prefix/Library/bin` 插入 PATH
- 同时设 `CUDA_VISIBLE_DEVICES=""` 阻止实际 GPU 使用
- detector.py 中原有的 `os.environ["CUDA_VISIBLE_DEVICES"] = ""` 修复在 import 时执行不是不够早——cuDNN 加载发生在模块 import 时，所以必须在 `run.py` 中处理

**相关文件**: `src/run.py`, `src/service/vision_module/vision_yolo/detector.py`

---

### 坑 9: SQLite WAL 文件未清理 → 跨重启残留数据

**现象**: 删除 `monitor.db` 重启后，View ID 不连续、设备显示 `streaming=true`、`create_view` 报 `"stream already in use"`

**根因**: SQLite WAL 模式下，数据分布在 `monitor.db`（主文件）、`monitor.db-wal`（日志）、`monitor.db-shm`（共享内存）三个文件中。`Remove-Item monitor.db` 只删除主文件，WAL/SHM 文件保留。下次 SQLite 连接时会从 WAL 文件中恢复上次未提交的事务，导致"已删除"的 View/设备数据复活。

**修复**: 清理时必须删除所有三个文件：`Remove-Item monitor.db* -Force`

**相关文件**: `src/extensions.py`（WAL 模式定义）

---

### 坑 10: asyncio.run() 取消后台 Task → 管线假启动

**现象**: create_view 返回成功、流可看，但无 YOLO 标注框。Server 日志无 `AIPipeline started` 消息。

**根因**: `view_task.py` 在 thread pool 线程中调用 `asyncio.run(start_pipeline(...))`。`start_pipeline` 内部通过 `asyncio.create_task()` 启动 `_run_loop` 和 `YamnetRunner`，但这些 Task 注册在 `asyncio.run()` 创建的临时事件循环上。当 `start_pipeline` 返回后，`asyncio.run()` 清理事件循环，**自动取消所有未完成的 Task**。管线被启动但立即被杀死。

**修复**: 使用专用后台线程 + 持久化事件循环：
```python
async def _pipeline_forever(...):
    await start_pipeline(...)
    while True:  # 保持循环不退出
        await asyncio.sleep(3600)

def _launch():
    asyncio.run(_pipeline_forever(...))

threading.Thread(target=_launch, daemon=True).start()
```

**相关文件**: `src/service/view_task.py`

---

### 坑 11: OpenCV FFmpeg 超时设置不生效

**现象**: FrameReader 打开不存在的 RTMP 流时等待 30 秒才超时，期望 5 秒

**根因**: `OPENCV_FFMPEG_CAPTURE_OPTIONS` 环境变量在 `vision_frame_reader.py` 的 `open()` 方法中设置，但 OpenCV 可能在库初始化时就读取该变量（而非每次 `VideoCapture` 构造时）。移到 `run.py` 中设置仍未完全生效（日志仍显示 30006ms）。

**当前状态**: 待修复。可能需要直接在 `cv2.VideoCapture` 调用中传参，或使用 `cv2.CAP_FFMPEG` 的 `timeout` opencv_option。

**相关文件**: `src/run.py`, `src/service/vision_module/vision_frame_reader.py`

---

### 坑 12: Python logging 未配置 → 应用日志不可见

**现象**: Server 启动后只能看到 uvicorn 的 access log 和 C 扩展的 stderr 输出。AI 管线、YOLO、FrameReader 的 `logger.info()` 输出完全不显示。

**根因**: 应用代码使用 `logging.getLogger(__name__)` 但从未调用 `logging.basicConfig()`。Python 默认 root logger 级别为 WARNING，所有 INFO 日志被过滤。

**修复**: 在 `src/run.py` 中添加：
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
```

**相关文件**: `src/run.py`

---

## 四、当前胶水代码变更总览

### Server 侧 (monitor-server)

```
src/run.py                          # +Library/bin PATH, +CUDA_VISIBLE_DEVICES, +logging.basicConfig, +OpenCV timeout
src/service/view_task.py           # +start_pipeline 调用, commit 提前, merge 跳过预检, +后台线程持久化
src/service/vision_task.py         # +register_video_ai_hooks (try/except)
src/service/vision_module/vision_pipeline.py  # +draw_part_b_overlay 调用
src/service/vision_module/vision_frame_reader.py  # 5s OpenCV 超时(待修复)
src/service/vision_module/vision_yolo/detector.py  # os.environ CUDA 保护(辅助)
src/network/wss/node_handler.py    # 心跳回传 device_map
src/extensions.py                  # SQLite WAL + busy_timeout
```

### Node 侧 (monitor-node)

```
network/wss_client.py              # 心跳合并 cached devices
network/command_handler.py         # 处理 device_map 消息
.env                               # WSS_PORT=8000
```

---

## 五、当前状态 & 下一步

- [x] 原始流可看 — VLC `rtmp://127.0.0.1:1935/live/USB_webcam_video_1`
- [x] Node ↔ Server WSS 通信正常，device_map 同步正常
- [x] UPDATE_STREAM 指令正常，Node 按需推流正常
- [x] 60 个回归测试全通过
- [x] 合流 `rtmp://127.0.0.1:1936/view/{id}` — 音频+视频可播放
- [x] YOLO 模型加载 — `yolo11n.pt` CPU 推理正常（cuDNN 修复后）
- [x] create_view 响应时间 ~8s（含 5s sleep 等待 Node 推流）
- [x] AI 管线后台线程持久化 — YAMNet/TensorFlow 模型加载中
- [ ] FrameReader 拉流——OpenCV 30s 超时过长，需确认 5s 修复生效
- [ ] 标注框可见——待 FrameReader 成功拉流 + YOLO 推理后验证
- [ ] 中文设备名 URL 编码 — ffprobe/ffmpeg 兼容性
- [ ] Web 前端的流播放对齐（目前仅 VLC RTMP）
- [ ] DB 清理脚本——删除 `monitor.db*` 而非仅 `monitor.db`

---

## 六、快速诊断命令

```bash
# 确认 RTMP 服务存活
curl -s http://127.0.0.1:8000/health

# 确认 Node 在线
curl -s http://127.0.0.1:8000/api/v1/nodes/ -H "Authorization: Bearer $TOKEN"

# 确认设备已同步
curl -s http://127.0.0.1:8000/api/v1/nodes/1/videos -H "Authorization: Bearer $TOKEN"

# 探测 RTMP 流是否存在
ffprobe -v quiet -show_entries stream=codec_type "rtmp://127.0.0.1:1935/live/USB_webcam_video_1"

# 列出活跃 View
curl -s http://127.0.0.1:8000/api/v1/views/ -H "Authorization: Bearer $TOKEN"
```
