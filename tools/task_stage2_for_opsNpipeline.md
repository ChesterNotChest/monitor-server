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
- [x] ⚠️ dlib 上传时 SIGSEGV（§8.4），离线提取 encoding 绕过

## 五、音频合流缺口

当前 AI 管线为 video-only。Audio 流需要合入最终流。

**问题**：pipe:0 + RTMP 音频双输入在同一个 ffmpeg 中死锁。纯 RTMP→RTMP 方式已验证可工作（两阶段方案），但中间流增加延迟。

- [ ] 5.1 方案选择：SRS 合流（运维域）vs Server 侧两阶段合流（自己可控）
- [ ] 5.2 若选 Server 侧：需要解决中间流延迟问题（anullsrc 占位 + 后续热切换真实音频？）
- [ ] 5.3 无论选哪种，记下当前缺口便于后续接手

## 六、已知搁置项

| 项目 | 状态 | 原因 |
|------|------|------|
| Node 累积延迟 | 修复中 | 采集 30fps→17fps + nobuffer + 4M；待验证 |
| Fence 围栏标注 | ✅ 已测 | 2026-07-12 验证：`db.commit()` 修复后 TTL 重载正常，橙色半透明围栏成功绘制到流上 |
| 时间戳嵌入 | ✅ 减弱 | Node drawtext 始终在跑（`ffmpeg_dshow.py` line 90），延迟问题已通过 nobuffer+4M+GOP false+17fps 组合缓解，obs age=75ms 不影响。Server 侧 cv2.putText 方案未做 |
| EventBus 订阅静默失败 | Workaround | `video_ai_processor.py` 直接更新全局 dict |
| PyAV 替代 subprocess | 搁置 | 按需，当前 ffmpeg pipe 足够稳 |

## 七、围栏 API 注入路径

### 7.1 围栏 CRUD

所有操作需要 `fence:manage` 权限（`security_guard` / `operator` 角色）。**URL 已统一**: wwh 合并后所有端点统一尾斜杠 `/`，307 问题已根治（§8.2）。

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

## 八、踩坑记录

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
