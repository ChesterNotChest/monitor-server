# 任务2 — Server 管线变动

**接手范围**: Python 代码（`monitor-server/src/`）
**依赖**: 无外部输入即可开工；NVENC 参数确认后补充编码器回退逻辑

---

## 一、上下文

AI 管线全链路已打通，`rtmp://127.0.0.1:1936/view/{id}` 可播放 YOLO 标注流。以下任务是联调中发现的代码 Bug 和性能优化项，全部落在 Server 侧 Python 代码。

已修复项（了解即可，无需改动）：cuDNN 崩溃、管线假启动、audio URL 错误、drain 缺失、原始合流冲突、GPU device 类型转换、logging 配置。

---

## 二、改动理由

### Bug 1: Part B 覆盖层返回值被丢弃

**文件**: `src/service/vision_module/vision_pipeline.py:178-179`

```python
annotated = draw_detections(frame, detections)       # ← 有 YOLO 框
draw_part_b_overlay(frame, ctx.tracks if ctx.tracks else [])  # ← 返回值没人接！
```

`draw_part_b_overlay` 内部做了 `frame.copy()` 并在副本上绘制 Track ID / Face / Action / Fence，返回副本。调用处丢弃了返回值。**后果：推送到 :1936 的流只有 YOLO 框，没有 ByteTrack ID、Face 标签、Action 标签、Fence 多边形。**

修复（快速）：`annotated = draw_part_b_overlay(annotated, ...)`

### Bug 2: face_labels 未传入

**文件**: 同上行。`draw_part_b_overlay` 需要显式传入 `face_labels=`，调用时未传。需从全局 `_face_labels` 或 EventBus 缓存取得后传入。

---

## 三、一步到位方案（替代 Bug 1+2）

当前两遍绘制：

```
draw_detections(frame, detections)         → YOLO 框 + "person"
draw_part_b_overlay(annotated, tracks)     → 再画一遍框 + "ID 3" + "Face: 张三"
```

改为：在 YOLO 出 detections 后、`draw_detections` 前，用 ByteTrack track_id 和 Face label **改写 detection 的标签字段**，`draw_detections` 一次性画完。好处：

- 不需要 `draw_part_b_overlay` 的 `frame.copy()`（省 640×480×3 全帧拷贝，~1ms/帧）
- **Bug #1 和 #2 直接消失**——不再调用 `draw_part_b_overlay`，也就不存在返回值丢弃和参数缺失
- 单遍绘制，GPU/CPU 各只干一次

涉及改动：`vision_pipeline.py` 主循环 + `vision_annotation.py` 的 Detection 标签字段。

**如果走这个方案，Bug 1 和 Bug 2 不用单独修**——它们涉及的代码路径被整条替换掉了。

---

## 四、编码器回退（依赖运维域确认 NVENC 参数后做）

**文件**: `src/service/vision_module/vision_merger.py`

当前写死 `libx264`。改为三级回退：

```
h264_nvenc  ← torch.cuda.is_available() → NVENC 独立编码芯片
    ↓ 不可用
h264_mf     ← Windows Media Foundation
    ↓ 不可用
libx264     ← CPU 软编（兜底）
```

检测逻辑 ~15 行。NVENC 正确参数：

```
-c:v h264_nvenc -preset p1 -tune ll -b:v 2M -rc vbr
```

等运维域在本机 RTX 4060 上确认该参数稳定后再写入。

---

## 五、Push 异步化（性能优化）

**文件**: 同上 `vision_merger.py`

当前 `push_frame` 里 `await proc.stdin.drain()` 把 libx264 的编码延迟反压回主循环，GPU/CPU 空转等编码。改为：

- 主循环只 `write()`，不 `drain()`
- 独立后台 task 专门 `drain()`
- 中间放 `asyncio.Queue(maxsize=2)`，队列满时主循环跳过 write（自然丢帧不阻塞）

这样编码延迟不再反压管线，GPU+CPU 可满负荷出帧。NVENC 启用后 drain 延迟从 ~25ms 降到 ~2ms，这个优化的紧迫性会大幅降低——建议先等 NVENC 确认，再决定是否异步化。

---

## 六、启动顺序

```bash
# Terminal 0 — RTMP :1935
cd monitor-node/rtmp_server && node index.js

# Terminal 1 — RTMP :1936
cd monitor-server/tools && node rtmp_debug_server.js

# Terminal 2 — Server (GPU)
cd monitor-server
$env:APP_DEBUG="false"; $env:DEBUG_WEB_STREAM="true"; $env:RTMP_DEBUG="true"; $env:YOLO_DEVICE="0"
python -m src.run

# Terminal 3 — Node
cd monitor-node
$env:RTMP_DEBUG="false"; $env:DEBUG_WSS="false"; $env:SERVER_BASE_URL="127.0.0.1"; $env:WSS_PORT="8000"; $env:RTMP_PORT="1935"
python run.py

# 测试
curl -X POST http://127.0.0.1:8000/api/v1/views/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":1,"audio_id":1}'
# VLC 打开响应中的 rtmp_url
```

**注意**：如果 View 创建报 "stream already in use"，说明 WAL 文件残留了旧数据。删除 `monitor-server/monitor.db*` 三个文件后重启 Server 即可。
