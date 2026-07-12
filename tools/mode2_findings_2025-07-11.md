# Mode 2 联调发现报告

**日期**: 2026-07-11  
**状态**: AI 管线全链路打通，标注流可播放，存在已知 bug 和性能瓶颈

---

## 一、已修复的问题

| # | 问题 | 根因 | 修复 | 文件 |
|---|------|------|------|------|
| 1 | Server 进程在 create_view 时崩溃 | conda `Library/bin` 含 cuDNN DLL 但不在 PATH，TensorFlow 加载时 C 层硬崩溃 | `run.py` 启动时注入 PATH | `src/run.py` |
| 2 | AI 管线假启动（无标注输出） | `asyncio.run()` 在 `start_pipeline` 返回后取消所有后台 Task | 后台线程 + `while True: sleep(3600)` 持久化事件循环 | `src/service/view_task.py` |
| 3 | AI 合流音频 URL 错误 | `_build_audio_pull_url` 只用 `audio_{id}`，Node 实际推流用 `{name}_{type}_{id}` | 透传 `audio_name`，使用 `build_pull_url` | `src/service/vision_module/vision_merger.py` |
| 4 | 标注帧从未到达 ffmpeg | `proc.stdin.write()` 后缺 `await proc.stdin.drain()`，数据滞留在 Python 写缓冲区 | 加 `await proc.stdin.drain()` | `src/service/vision_module/vision_merger.py` |
| 5 | 原始合流覆盖 AI 合流 | 两个 ffmpeg 进程同时推同一 :1936 URL | 禁用 `ffmpeg_manager.start_merge`（原始合流） | `src/service/view_task.py` |
| 6 | GPU 模式下 YOLO 加载失败 | `model.to("0")` 传字符串，PyTorch 期望 `int(0)` | `isdigit()` 检测后转 int | `src/service/vision_module/vision_yolo/detector.py` |
| 7 | 应用日志不可见 | 无 `logging.basicConfig()`，root logger 默认 WARNING 过滤 INFO | 在 `run.py` 中配置 | `src/run.py` |

---

## 二、改动理由

### Bug 1: Part B 覆盖层返回值被丢弃

**文件**: `src/service/vision_module/vision_pipeline.py:178-179`

```python
annotated = draw_detections(frame, detections)       # ← 有 YOLO 框
draw_part_b_overlay(frame, ctx.tracks if ctx.tracks else [])  # ← 返回了新帧，但没人接！
```

`draw_part_b_overlay` 内部做了 `frame.copy()` 并在副本上绘制 Track ID / Face / Action / Fence，返回副本。但调用处丢弃了返回值。**后果：推送到 :1936 的流只有 YOLO 框，没有 ByteTrack ID、没有 Face 标签、没有 Action 标签、没有 Fence 多边形。**

修复：`annotated = draw_part_b_overlay(annotated, ...)`

### Bug 2: face_labels 未传入 draw_part_b_overlay

**文件**: `src/service/vision_module/vision_pipeline.py:179`

```python
draw_part_b_overlay(frame, ctx.tracks if ctx.tracks else [])
#                    ↑ 缺少 face_labels, action_labels, fence_labels
```

全局 `_face_labels` 通过 EventBus `FACE` topic 正常更新，但 `draw_part_b_overlay` 的参数签名要求显式传入 `face_labels=`，调用时未传。**后果：即使 Face 识别器工作正常，人脸标签也不会画到流上。**

### Bug 3: dlib API 不兼容导致人脸特征提取全部失败

**文件**: conda 环境 `dlib` + `face_recognition` 版本组合

dlib 升级到 pybind11 后 C++ 绑定的参数签名改变。`face_recognition.face_encodings()` 内部按旧 API 调用 `compute_face_descriptor(image, raw_landmark_set, num_jitters)`，新 dlib 不接受这个参数顺序，抛出：

```
TypeError: compute_face_descriptor(): incompatible function arguments
```

**后果链**：
1. `upload_avatar` → `extract_face_encoding()` → `face_recognition.face_encodings()` → 崩溃，返回 None
2. `feat_json_id` 永远为 NULL
3. `FaceRecognizer.load_known_people()` 加载不到任何已知人员
4. 实时识别永远返回 STRANGER

**修复方向**：降 dlib 到 `<19.24` 或升 face_recognition 到兼容新 pybind11 dlib 的版本。ls2 分支已验证过模型能力，属纯环境版本问题。

---

## 三、性能瓶颈分析

### 当前管线结构（完全串行）

```
read()           → YOLO(GPU)       → Draw(CPU)     → push_frame()
sync I/O, 33ms    sync GPU ~5ms     sync CPU ~1ms    write + drain(等ffmpeg编码)
```

四个模块串行执行，**任何一步的延迟直接叠加到帧间隔**。硬件（GPU/CPU）在同一时刻只有一个在工作。

### 模块间并行可行性

| 尝试 | 可行性 | 原因 |
|------|--------|------|
| Reader ∥ YOLO | ✗ | 同一帧，YOLO 依赖 Reader 输出 |
| YOLO ∥ Draw | ✗ | 同一帧，Draw 依赖 YOLO detections |
| Draw ∥ Push(同帧) | ✗ | 同一帧，Push 依赖 Draw 输出 |
| **YOLO(帧N+1) ∥ Push(帧N)** | **✓** | 不同帧，无数据依赖 |

**唯一可行的并行**：把 Push 从主循环中拆出来，变成独立的后台 task。主循环只做 `write`（不 drain），后台 task 专门做 `drain`。

### 为什么 drain 是瓶颈

`await proc.stdin.drain()` 等待 ffmpeg 消费 pipe 中数据。libx264 CPU 软编每帧 ~20-30ms，`drain()` 在此期间阻塞主循环。GPU（刚算完 YOLO）和 CPU（刚画完框）都在空转等编码完成。

### 优化选项（不涉及架构改动）

| 方案 | 改动量 | 预期效果 |
|------|--------|---------|
| `FPS_TARGET=10` | 改配置 | 帧数 -33%，延迟同比例下降 |
| 分辨率 320x240 | 改配置 | 像素数 -75%，编码/推理/绘制全链路加速 |
| NVENC 硬编 | 改 vision_merger 编码器参数 | 编码延迟从 ~25ms 降到 ~2ms，drain 不再阻塞 |
| Push 异步化 | Pipeline 加 Queue + 独立 drain task | 编码延迟不再反压管线 |

---

## 四、编码器选型优化

### 现状

| 位置 | 当前编码器 | 硬件 | 问题 |
|------|-----------|------|------|
| Node 推流 | `h264_mf` (Windows MF 硬编) | 集成显卡 | **已最优**，无需改动 |
| Server AI 合流 | `libx264` (CPU 软编) | — | 跟 YOLO、Python 抢 CPU，drain 阻塞 20-30ms |

### Server 编码器优先级

```
h264_nvenc  ← torch.cuda.is_available() → NVIDIA 独显编码芯片（与 CUDA Core 独立，互不抢占）
    ↓ 不可用
h264_mf     ← Windows Media Foundation（任何有 GPU 的 Win10+ 都支持）
    ↓ 不可用
libx264     ← CPU 软编（兜底）
```

RTX 4060 的 NVENC 是独立硅片，编码时不影响 YOLO 推理用的 CUDA Core。编码延迟从 libx264 的 ~25ms/帧 降到 ~2ms/帧，pipe `drain()` 几乎不再阻塞。

### 关于延迟

VLC 看到的 ~2 秒固定延迟来自缓冲层叠，不是编码器速度：

```
dshow 缓冲 → 编码器内部缓冲(3-5帧) → RTMP GOP cache → VLC 缓冲
  ~30ms        ~100-170ms              ~1-2秒         ~0.5秒
```

Node 已用 `h264_mf` 最快编码，延迟在 GOP cache 这层——node-media-server 默认 `gop_cache: true` 攒完整 GOP 才下发。真正低延迟需要 WebRTC（UDP 直推），但当前 RTMP 调试阶段没必要换——架构已预留 SRS（`srs-bin/srs.exe`），Web 前端联调时切协议即可。

### NVENC 失败的已知问题

之前测试 `h264_nvenc` 时 ffmpeg 进程直接断开（`ConnectionResetError`），原因是参数不完整。裸 `-c:v h264_nvenc` 在部分驱动版本上不稳定，需要加：

```
-c:v h264_nvenc -preset p1 -tune ll -b:v 2M -rc vbr
```

`p1` = 最低延迟 preset，`ll` = low latency tune。这两个参数加上后编码器才会以最低延迟模式运行。

---

## 五、关于 face_label 挂载到 YOLO 框

当前是两遍绘制：

```
draw_detections(frame, detections)         → YOLO 框 + "person"
draw_part_b_overlay(annotated, tracks)     → 再画一遍框 + "ID 3" + "Face: 张三" (但返回值被丢弃)
```

合理方案：在 YOLO 出 detections 后、`draw_detections` 前，用 ByteTrack track_id 和 Face label **改写 detection 的标签字段**，让 `draw_detections` 一次性画完。好处：

- 不需要 `draw_part_b_overlay` 的 `frame.copy()`（省 640×480×3 全帧拷贝）
- Bug #1 和 #2 直接消失（不再需要第二遍绘制）
- 单遍绘制，GPU/CPU 各只干一次

---

## 六、SRS + WebRTC 联调对齐指引

### 本地开发环境

SRS Windows 安装包已提交：`srs-bin/srs-setup.exe`。安装后 `srs.exe` 在 `C:\Program Files\SRS\`（或安装时指定路径）。本地配置文件 `srs/srs.conf` 已预置。

### 启动（替代 rtmp_debug_server.js）

```powershell
# 替换 Terminal 1 的 RTMP 靶子
.\srs-bin\srs.exe -c srs\srs.conf
```

SRS 监听：
- `:1935` — RTMP（ffmpeg 推流入口，无需改动）
- `:8080` — HTTP-FLV / HTTP API
- `:8000` — WebRTC（WHEP 拉流）

### Server 切换

```bash
DEBUG_WEB_STREAM=false  # 切换到 SRS 模式
```

`build_play_urls` 在非 debug 模式下自动返回 `webrtc_url`，前端直接 `GET /api/v1/views/{id}` 取地址。

### 验证序列

```bash
# 1. ffmpeg 推流（Server 自动完成）
# 2. RTMP 检查
ffprobe rtmp://127.0.0.1:1936/view/1

# 3. WebRTC 检查（浏览器打开）
# http://127.0.0.1:8080/players/whep?app=view&stream=1
```

### 与 Web 前端对齐的关键点

| 事项 | 说明 |
|------|------|
| SRS WHEP URL 格式 | `http://host:port/rtc/v1/whep/?app=view&stream={view_id}` |
| 前端只需 | `GET /api/v1/views/{id}` → `response.webrtc_url` → 传给播放器 |
| CORS | SRS HTTP :8080 需配 `access_control_allow_origin` |
| 延迟预期 | RTMP ~2s → WebRTC ~200ms |

---

## 七、当前代码变更清单

```
src/run.py                          # +Library/bin PATH, +logging.basicConfig
src/service/view_task.py            # +后台线程持久化管线, 原始合流已禁用
src/service/vision_task.py          # +audio_name 透传
src/service/vision_module/vision_pipeline.py  # +audio_name 参数
src/service/vision_module/vision_merger.py    # +drain(), +audio_name URL修正
src/service/vision_module/vision_yolo/detector.py  # +GPU device int转换
```

---

## 八、分工建议

任务沿模块边界天然拆成三块，互不阻塞。

**Server 管线**（改 Python 代码）。承接 Bug #1（Part B 返回值丢弃）、Bug #2（face_labels 未传入），以及 §五 的 face_label 挂 YOLO 框方案。这三个改动的交集在 `vision_pipeline.py` 的主循环里，同一个人一次改完比拆开效率高。NVENC 编码器回退逻辑加在 `vision_merger.py`，改动量很小（~15 行检测 + 参数拼接），但需要等运维域给出"h264_nvenc 在本机可用"的确认。Push 异步化也是同一个文件、同一个人，避免跟 Bug 修复冲突。

**运维/环境**（不写 Python）。两件事：一是 WAL 清理加入启动流程——目前每次重启 Server 如果 `monitor.db-wal` 残留，View 创建就会报 "stream already in use"，需要在启动脚本或 `run.py` 里加清理逻辑。二是在 GPU 实机上调试 NVENC 参数——验证 `h264_nvenc -preset p1 -tune ll -b:v 2M` 能否稳定推流，然后把最终可用的编码器参数交给 Server 域。conda 环境里 dlib 与 face_recognition 的 API 兼容问题也归这里（ls2 分支已验证过模型能力，大概率是 conda 包版本导致）。

**Web 前端**（独立验证，不碰 AI 代码）。启动 SRS（`srs-bin/srs.exe -c srs/srs.conf`）替代 `rtmp_debug_server.js`，Server 设 `DEBUG_WEB_STREAM=false` 后 `GET /api/v1/views/{id}` 会返回 `webrtc_url`。前端只需拿这个 URL 喂给 WebRTC 播放器即可。联调过程本身也在验证 §七 的 SRS 配置是否正确，为后续 Web 端正式接入铺路。

三块的唯一一次对接：运维域确认 NVENC 可用参数 → Server 域写入 `vision_merger.py`。除此之外无交集，可并行开工。

---

## 十、讨论要点

1. Bug #1/#2 立即修，还是直接用 §五 方案一步到位？（后者省一次 `frame.copy()` 且两个 bug 直接消失）
2. 编码器优先级：先修 NVENC 参数、再降分辨率、还是先 Push 异步化？
3. WAL 模式已改回 DELETE（`extensions.py`），确认不再有残留文件问题？
4. Bug 3（dlib 兼容）——降 dlib 还是升 face_recognition？修好后 §八的编码提取测试就不再 skip
