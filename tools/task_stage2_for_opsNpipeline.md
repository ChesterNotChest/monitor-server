# Stage 2 任务清单 — 运维 + 管线收尾

**接手范围**: `E:/AI/monitor-server`（monitor-server + monitor-node 两侧）
**基准**: Merge ls2→chester 后，245 passed

---

## 一、Playbook 验证 ✅ (2026-07-11)

merge 后全链路确认可用。

- [x] 1.1 双靶子启动（:1935 rtmp_server + :1936 rtmp_debug_server）
- [x] 1.2 Node 启动（h264_mf + drawtext 烧时间戳）
- [x] 1.3 Server 启动（`DEBUG_WEB_STREAM=true YOLO_DEVICE=0 APP_DEBUG=false PORT=8002`）
- [x] 1.4 创建 View 1 → VLC 播放 `rtmp://127.0.0.1:1936/view/1`
- [x] 1.5 确认：r_frame_rate=10/1、Person ID N 标注正常、右下角有 Node 时间戳
- [x] 1.6 确认 obs 日志输出正常：`[obs] FPS=10.0 | r=0 y=16 pipe=16 frame_age=2ms`

### 基线 v3 (2026-07-11 最终)

```
FPS_TARGET=17  (Node 采集上限 17fps，Server 17fps 处理，全链路对齐)
h264_nvenc -preset p1 -zerolatency 1
Node: -framerate 17 -fflags nobuffer -rtbufsize 4M -b:v 1M
obs:  r=0ms  y=16ms  hk=0ms  pipe=16ms  push=17fps  帧率对齐
标注: Person ID N + Face: Stranger + Sitting (枚举 16 类)
可视化: 浅绿虚线框 = SlowFast padded crop (+30%)
```

## 二、FrameReader 鲁棒性修复 ✅ (2026-07-11)

当前 `_run_loop` 遇到 `FrameReaderState.ERROR` 直接 `break` 管线永久死亡。改为重试循环。

- [x] 2.1 `_run_loop` 中 `FrameReader.ERROR` 时不再 break，调用 `_reopen_reader()`（指数退避 2s→60s，最多 10 次）
- [x] 2.2 重试日志：`FrameReader reopen attempt N/10 in X.Xs ...` → `FrameReader reopened successfully (attempt N)`
- [x] 2.3 验证：:1935 kill→restart 后管线 attempt 4 自动恢复，obs 显示 `FPS=10.0 | r=0` 稳态
- [x] 附带修复：`:1935 rtmp_server/index.js` 的 `gop_cache: true→false`（长 GOP 导致新客户端 30s 超时）
- [x] 附带修复：`start()` 中首次 `_reader.open()` 失败不再阻止管线启动，交由 `_run_loop` 重试
- [x] 附带修复：`FrameReader._handle_read_failure()` 删除 `_last_url` 死代码；新增 `reset_error()`
- [x] 245 passed

## 三、标注信息补全 ✅ (2026-07-11)

- [x] Face: Stranger 显示正常（dlib + C2 持久缓存 + 增量更新）
- [x] Action: Sitting/Standing/Waving 等显示正常（SlowFast AVA+Kinetics 双模型 + 线程池）
- [x] 枚举同步：`constants.py` 16 类对齐 `seed_data.py` ACTION_NAMES
- [x] 可视化：浅绿虚线框标注 SlowFast padded crop 区域 + 橙色半透明围栏区域
- [x] Fence：围栏检测 + 标签 + 绘制全部就绪。FenceEngine 5s TTL 缓存 DB 查询
- [x] 事件总线 Bug：workaround 绕过，`video_ai_processor.py` 直接更新全局 dict
- [x] **SPEC**: 围栏生命周期严格包含于 View 生命周期。即需要等待view创建后，才能用API画围栏。View 存在并运行时，FenceEngine 每 5s 从 DB 重载围栏配置。围栏 API 创建/修改/删除后最多 5s 自动生效，无需重启管线
- [x] 250 passed

## 四、人脸识别恢复 ⏳ (代码已恢复，待引导测试)

### 4.1 代码恢复 ✅

- [x] 4.1.1 `video_ai_processor.py`：已恢复 `face_recognizer.recognize_and_publish()` 
- [x] 4.1.2 `video_ai_processor.py`：已恢复 `slowfast_runner.enqueue_and_publish()`
- [x] C2 人脸缓存：同 track_id 只识别一次，后续帧零开销
- [x] Face 标签增量更新（不清空已有标签）
- [x] SlowFast 线程池：推理不阻塞主循环

### 4.2 引导测试 ✅ (2026-07-12)

- [x] 4.2.1 `POST /api/v1/persons/` 创建人物 Chester
- [x] 4.2.2 `POST /api/v1/persons/{id}/avatar` 上传头像 → 128D encoding 入库
- [x] 4.2.3 重启管线 → Face: Chester (track 1 & 42)
- [x] ⚠️ dlib 上传时 SIGSEGV（§9.4），离线提取 encoding 绕过

## 五、视频延迟优化 🔴 当前优先

Video-only 管线的端到端延迟需要压到可接受范围，**必须在音频合流之前完成**（合流会引入额外缓冲，叠在未修复的延迟上会让问题更难定位）。

### 5.1 现象

- VLC 播放 AI 标注流时主观延迟偏高
- **"隔夜效应"**: 没改代码的情况下，第二天重新开机 → 延迟明显降低；长时间不关机 → 延迟逐渐升高
- 怀疑根因：ffmpeg 缓冲随时间累积（TCP buffer creep + 内部 demuxer buffer + OpenCV VideoCapture buffer）

### 5.2 管线缓冲点全景

每个环节都是一个潜在的缓冲堆积点：

```
摄像头 dshow
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ ① Node ffmpeg pull (dshow → RTMP 推流)               │
│    dshow 内部缓冲 → ffmpeg demuxer → 编码器队列       │
│    → RTMP 输出缓冲 → TCP send buffer                   │
│    参数: -framerate 17 -fflags nobuffer -rtbufsize 4M │
└──────────────────────────────────────────────────────┘
    │  RTMP :1935/live/
    ▼
┌──────────────────────────────────────────────────────┐
│ ② Server FrameReader (RTMP → OpenCV)                  │
│    cv2.VideoCapture(CAP_FFMPEG) 拉流                  │
│    仅设 OPENCV_FFMPEG_CAPTURE_OPTIONS="timeout;..."   │
│    ⚠ 没有 nobuffer / rtbufsize / probesize 控制      │
│    ffmpeg 内部 demuxer buffer ← 主要嫌疑              │
│    TCP receive buffer ← OS 层，长时间运行会涨          │
└──────────────────────────────────────────────────────┘
    │  BGR24 frame
    ▼
┌──────────────────────────────────────────────────────┐
│ ③ YOLO 推理 + 标注                                    │
│    ~16ms 单帧，无显式队列                              │
│    时钟门控维持 17fps 节奏                            │
└──────────────────────────────────────────────────────┘
    │  annotated frame (pipe:0)
    ▼
┌──────────────────────────────────────────────────────┐
│ ④ Server ffmpeg push (rawvideo pipe → 编码 → RTMP)   │
│    NVENC -zerolatency 1 -delay 0                      │
│    RTMP 输出缓冲 → TCP send buffer                     │
│    编码器内部 lookahead/reorder 队列                   │
└──────────────────────────────────────────────────────┘
    │  RTMP :1935/view/
    ▼
┌──────────────────────────────────────────────────────┐
│ ⑤ VLC 播放缓冲                                        │
│    默认 network-caching=1000ms                        │
│    可在 VLC 偏好设置中调低                             │
└──────────────────────────────────────────────────────┘
```

**主要嫌疑排序**（按影响大小）:
1. **② FrameReader OpenCV/ffmpeg 缓冲** — 缺乏任何 buffer control flag，「隔夜效应」的最大嫌疑人
2. **① Node ffmpeg 缓冲** — 已有 `nobuffer + rtbufsize 4M`，但 dshow 内部缓冲不可控
3. **④ Push 编码器队列** — `-zerolatency 1 -delay 0` 已做，但 `-g 30` 可能引入 1 帧延迟
4. **⑤ VLC** — 用户侧可控，不是服务端问题

### 5.3 修复范式：感知 → 修复 → 验证（多轮迭代）

```
Round N:  [感知] 测全链路延迟 → [修复] 一个变量 → [验证] 对比 before/after → 下一个嫌疑
```

每轮只改一个变量，对比效果后再进入下一轮。如果某轮修复无效则回退。

#### 5.3.1 感知工具（Round 1 必须先做）

当前唯一的延迟信号是 `[obs] frame_age=XXms`（从 FrameReader `_open_time` 算的墙上时间差）。这个数字只反映 Server 内部的帧龄，**不反映 RTMP 缓冲堆积**。

需要新增的观测点：

- [ ] **5.3.1.1 FrameReader 帧时间戳 vs 墙上时间** — `frame_age = time.time() - frame_capture_time`。如果 frame_age 持续增长（比如从 50ms 涨到 2000ms），说明 Reader 的 RTMP 缓冲在堆积。当前已有 frame_age（`vision_pipeline.py` obs 行），但需要确认它测量的是真实帧龄还是自 Reader 打开后的偏移
- [ ] **5.3.1.2 RTMP 源流 ffprobe 时间戳** — `ffprobe -show_packets rtmp://127.0.0.1:1935/live/...` 对比 `pts` 和 `pts_time`，看 SRS 侧的缓存深度
- [ ] **5.3.1.3 Node 推流侧 latency 测量** — Node 的 obs 日志目前没有 frame_age 概念。建议加 Node 侧的采集时间戳
- [ ] **5.3.1.4 端到端钟表测试** — 在摄像头前放一个显示秒数的手机/网页时钟，用 VLC 截图对比画面中的时间和真实时间，差值 = 端到端延迟。这是最直接的金标准

#### 5.3.2 Round 1 修复候选：FrameReader 侧缓冲控制

FrameReader (`vision_frame_reader.py:77`) 当前只用 `cv2.VideoCapture(url, cv2.CAP_FFMPEG)`，没有传任何 ffmpeg 参数。OpenCV 的 `cv2.CAP_FFMPEG` 后端支持通过环境变量或 `cv2.CAP_PROP` 传参，但最可靠的方式是：

- [ ] **5.3.2.1 尝试 `cv2.CAP_PROP_BUFFERSIZE`** — `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)` 限制 OpenCV 内部缓冲帧数（部分 OpenCV 版本支持）
- [ ] **5.3.2.2 尝试 OPENCV_FFMPEG_CAPTURE_OPTIONS** — 当前已设 `timeout;5000000`，可以追加 RTMP/协议级参数如 `rtmp_live;live|buffer_size;1024`（需验证 OpenCV 是否真的传递给了 ffmpeg）  
- [ ] **5.3.2.3 兜底：绕过 OpenCV，直接用 ffmpeg subprocess + named pipe** — 类似 push 侧的做法。`ffmpeg -fflags nobuffer -rtbufsize 1M -i rtmp://... -f rawvideo pipe:1` → Python 从 pipe 读帧。这是最彻底但工程量最大的方案，如果在 5.3.2.1/5.3.2.2 两轮都无效才启用

#### 5.3.3 Round 2 修复候选：帧率对齐 + 跳帧策略

- [ ] **5.3.3.1 确认三段帧率一致性** — 采集帧率 (dshow) = 推流帧率 (Node `-framerate`) = 处理帧率 (Server `FPS_TARGET`) = 推流帧率 (Server `-r`)。当前应该都是 17，用 `ffprobe` 分别验证各段实际 r_frame_rate
- [ ] **5.3.3.2 如果存在帧率漂移** — 原理：Node 侧 dshow 实际输出 30fps 而 `-framerate 17` 让 ffmpeg 丢帧 → 丢帧逻辑可能不精确 → 时序抖动累积 → 缓冲。考虑在 Server push 侧用 `-vsync passthrough` 替代 `-vsync cfr` + `-copyts` 保留原始时间戳贯通全链路

#### 5.3.4 Round 3 修复候选：push 侧微调

- [ ] **5.3.4.1 减小编码器 GOP** — 当前 `-g 30`（约 1.8s 的 GOP）。改为 `-g 17`（约 1s）减少关键帧间隔，降低 VLC 重连延迟
- [ ] **5.3.4.2 加 RTMP 输出缓冲控制** — push 侧 ffmpeg 命令追加 `-rtmp_buffer 100 -buffer_size 256k`（毫秒级缓冲）
- [ ] **5.3.4.3 VLC 播放缓冲** — `network-caching=300`（默认 1000ms），在 VLC → 工具 → 偏好设置 → 输入/编解码器中调整

### 5.4 验证标准

每一轮修复后，用以下标准判断是否成功：

| 指标 | 当前基线 | 目标 |
|------|---------|------|
| 端到端延迟（钟表法） | 待测 | <3s |
| `frame_age` 稳态 | 待测 | <100ms 且不随时间增长 |
| `frame_age` 漂移率 | 待测 | 运行 30min 后仍在 <300ms |
| 隔夜效应 | 存在 | 消除（连续运行 1h 后重新推流，延迟不涨） |

---

## 六、音频合流缺口 ⏸️ 阻塞于 §五

当前 AI 管线为 video-only。Audio 流需要合入最终流。

**阻塞原因**: 音频合流（两阶段方案）会引入额外缓冲延迟。必须先在 §五 把 video-only 管线延迟压到目标范围，确立干净基线后再做合流。

**问题**：pipe:0 + RTMP 音频双输入在同一个 ffmpeg 中死锁。纯 RTMP→RTMP 方式已验证可工作（两阶段方案），但中间流增加延迟。

- [ ] 6.1 方案选择：SRS 合流（运维域）vs Server 侧两阶段合流（自己可控）
- [ ] 6.2 若选 Server 侧：需要解决中间流延迟问题（anullsrc 占位 + 后续热切换真实音频？）
- [ ] 6.3 无论选哪种，记下当前缺口便于后续接手

## 七、已知搁置项

| 项目 | 状态 | 原因 |
|------|------|------|
| Node 累积延迟 | → §五 专项 | 已拆为独立任务：感知→修复→验证多轮迭代 |
| Fence 围栏标注 | ✅ 已测 | 2026-07-12 验证：`db.commit()` 修复后 TTL 重载正常，橙色半透明围栏成功绘制到流上 |
| 时间戳嵌入 | ✅ 减弱 | Node drawtext 始终在跑（`ffmpeg_dshow.py` line 90），延迟问题已通过 nobuffer+4M+GOP false+17fps 组合缓解，obs age=75ms 不影响。Server 侧 cv2.putText 方案未做 |
| EventBus 订阅静默失败 | Workaround | `video_ai_processor.py` 直接更新全局 dict |
| PyAV 替代 subprocess | 搁置 | 按需，当前 ffmpeg pipe 足够稳 |

## 八、围栏 API 注入路径

### 7.1 围栏 CRUD

所有操作需要 `fence:manage` 权限（`security_guard` / `operator` 角色）。**URL 已统一**: wwh 合并后所有端点统一尾斜杠 `/`，307 问题已根治（§9.2）。

```powershell
# 认证
$TOKEN = (Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/v1/auth/login/" -Method POST `
  -ContentType "application/json" `
  -Body "{`"username`":`"admin`",`"password`":`"<PWD>`"}").access_token

# 列出所有围栏
GET /api/v1/fences/
# → [{id, name, view_id, coords:[[x,y],...], dwell_time, density, leave_frames}]

# 创建围栏（view 必须先存在）
POST /api/v1/fences/
Body: {
  "name": "区域-A",
  "view_id": 1,
  "coords": [[100,100],[500,100],[500,380],[100,380]],   # 4 点不规则四边形，像素坐标系
  "dwell_time": 10,    # 停留时限 (秒)，可选，默认 10
  "density": 0.6,      # 密度阈值 (0~1)，可选，默认 0.6
  "leave_frames": 5    # 离开判定帧数，可选，默认 5
}

# 更新围栏坐标
PUT /api/v1/fences/{fence_id}/
Body: { "coords": [[...],[...],[...],[...]] }

# 删除围栏
DELETE /api/v1/fences/{fence_id}/  → 204 No Content
```

### 7.2 围栏生命周期

```
          POST /fences/                          DELETE /fences/{id}/
              │                                        │
              ▼                                        ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│  DB: electronic_fences       │      │  DB: 围栏记录删除             │
│  └─ 持久化                   │      │  └─ FenceEngine 最多 5s 感知 │
└──────────────────────────────┘      └──────────────────────────────┘
              │                                        │
              ▼                                        ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│  FenceEngine TTL 5s          │      │  流上围栏多边形消失           │
│  └─ 从 DB 重载围栏          │      │  流上围栏多边形消失           │
│  └─ ctx.fence_polygons 注入  │      │  ctx.fence_polygons 变为 []  │
└──────────────────────────────┘      └──────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  vision_pipeline.py          │
│  └─ draw_fence_polygons()    │
│     └─ 橙色半透明覆盖 (alpha=0.2)│
│        → :1936 RTMP 流       │
└──────────────────────────────┘
```

**关键约束**: 围栏生命周期严格包含于 View 生命周期。必须先创建 View，再创建围栏。删除 View 时围栏不会自动删除（DB 有 `RESTRICT` 约束）。

### 7.3 前端侧边栏数据流

对于前端侧边栏展示围栏信息，现有 API 已经可以支撑三层数据：

```
┌─────────────────────────────────────────────────────────────────┐
│  前端侧边栏                                                      │
│                                                                  │
│  ┌─ 围栏列表 ──────────────────────────────────────────────┐    │
│  │  GET /api/v1/fences/                                     │    │
│  │  → 围栏名称、多边形坐标、阈值参数                         │    │
│  │  → 配合 Canvas/SVG 在预览图上绘制围栏边界                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ 实时告警 ──────────────────────────────────────────────┐    │
│  │  GET /api/v1/events/?view_id=1                            │    │
│  │  → 围栏闯入事件（Created by AlertEngine）                 │    │
│  │  → 轮询间隔 ≤5s 即可（AlertEngine 检查周期 = 5s）        │    │
│  │  ⚠ 暂无 WSS 直推前端，如需实时推送需新增通道              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ 统计面板 ──────────────────────────────────────────────┐    │
│  │  GET /api/v1/events/stats/by-exception                       │    │
│  │  GET /api/v1/events/stats/trend?granularity=hour             │    │
│  │  → 围栏闯入次数 / 趋势图                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**数据流链路**（围栏事件从管线到侧边栏）:
```
FenceEngine.check() → FenceEvent
  → EventBus.publish(FENCE, ...)
    → AlertEngine._on_event() → 汇聚到内存池
      → 每 5s 匹配 ExceptionDef → 创建 SituationEvent → 写入 DB
        → GET /api/v1/events/?view_id=1 → 前端轮询 ✅
```

**当前缺口**: 前端侧边栏需要主动轮询 `/events/`，暂无服务端推送。Node ↔ Server 已有 WSS 通道，前端 ↔ Server 的 WSS 推送可复用类似模式（非本阶段范围）。

### 7.4 常用 API 路径

| 方法 | 正确 URL | 用途 | 权限 |
|------|---------|------|------|
| POST | `/api/v1/auth/login` | 登录 | — |
| GET | `/api/v1/auth/me` | 当前用户 | — |
| GET | `/api/v1/nodes/` | 列出节点 | — |
| GET | `/api/v1/nodes/{id}/videos/` | 节点的视频设备 | — |
| POST | `/api/v1/views/` | 创建视图 | — |
| GET | `/api/v1/views/` | 列出视图 | — |
| DELETE | `/api/v1/views/{id}/` | 删除视图 | — |
| GET | `/api/v1/fences/` | 列出围栏 | fence:manage |
| POST | `/api/v1/fences/` | 创建围栏 | fence:manage |
| PUT | `/api/v1/fences/{id}/` | 更新围栏 | fence:manage |
| DELETE | `/api/v1/fences/{id}/` | 删除围栏 | fence:manage |
| GET | `/api/v1/persons` | 列出人员 | — |
| POST | `/api/v1/persons` | 创建人员 | — |
| POST | `/api/v1/persons/{id}/avatar` | 上传头像 (multipart) | — |
| GET | `/api/v1/events` | 事件日志（?view_id=） | — |
| GET | `/api/v1/alerts` | 告警列表 | alert:list |

## 九、踩坑记录

### 8.1 `db.commit()` 缺失 → fence API 数据无法持久化 ✅ (2026-07-12)

**现象**: `POST /api/v1/fences/` 返回 `id=1` 成功，但 `GET /api/v1/fences/` 返回空数组。FenceEngine TTL 重载始终加载 0 条围栏。

**根因**: `BaseRepo.create/update/delete` 只做 `db.flush()` 不 `db.commit()`。`get_db()` 构造的 Session（`autocommit=False`）关闭时只 `close()` 不 commit，未提交的事务回滚，数据消失。

`view_task.py` 正确 —— 显式调了 `db.commit()`。`fence_task.py` 遗漏。

**修复** (`fence_task.py`):
- `create_fence`: `repo.create(...)` → `db.commit()`
- `update_fence`: `repo.update(...)` → `db.commit()`
- `delete_fence`: `repo.delete(...)` → `db.commit()`

**同类风险**: `detection_task.py` 等其他 Service 可能同有遗漏，待排查。

### 8.2 尾斜杠 307 重定向 → 丢失 CORS / Authorization 头 ✅ (2026-07-12)

**现象 A（前端）**: 浏览器请求 `/api/v1/views`（无尾斜杠）→ FastAPI 307 重定向到 `/api/v1/views/` → 307 响应不含 `Access-Control-Allow-Origin` → 浏览器 CORS 报错

**现象 B（API / 脚本）**: `GET /api/v1/fences/`（带尾斜杠）→ 307 重定向到 `/api/v1/fences` → 新请求不保留 Authorization header → 401

**根因**: Starlette 的尾斜杠重定向在 CORSMiddleware 之前处理。不同 router 定义了不同的 path 风格（`""` vs `"/"`），导致 URL 格式不统一。

**修复** (wwh 分支, 2026-07-12): 所有 router 路径统一使用 `"/"` 后缀：
- `fence_router`: `""` → `"/"`，`"/{fence_id}"` → `"/{fence_id}/"`
- 其他 router 同模式
- 效果：所有 API URL 统一带尾斜杠 `/`，307 重定向不再发生

**前端**: 合并 wwh 后所有端点都用尾斜杠 `/` 即可，无需逐个确认。

### 8.3 Server 重启后 Node 设备 ID 偏移

**现象**: Server 重建 DB 后重启，Node 推送 RTMP 到 `..._video_0` 而 FrameReader 读取 `..._video_1`

**根因**: Node 的 device_id 由 Server WSS 下发映射表决定。Server DB 清空后设备重新注册，但 Node 未同步收到更新。

**规避**: Server 重建 DB 后需同步重启 Node。

### 8.4 dlib SIGSEGV 崩溃 → 头像上传 API 不稳定 ✅ (2026-07-12)

**现象**: `POST /api/v1/persons/{id}/avatar` 时 Server 进程 SIGSEGV 崩溃退出（无 HTTP 响应，curl 报 exit 56）

**根因**: `extract_face_encoding()` 把全尺寸 JPEG 直塞 `face_encodings(image)`，dlib C 层 `compute_face_descriptor` 在 Windows 上处理大图时 SIGSEGV。管线没崩是因为只传 50~150px 的人脸 crop。

**修复** (`face_image.py`): 借鉴管线同款路径——先 `face_locations` 找人脸 → `ascontiguousarray` crop → `face_encodings(crop, locations)`，ABI 不兼容时回退不带 locations。
```
之前: load_image_file → face_encodings(full_img)        → SIGSEGV
现在: load_image_file → face_locations → crop → encode  → HTTP 200 ✅
```
