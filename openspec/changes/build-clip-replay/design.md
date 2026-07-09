## Context

`SituationEvent` 记录异常事件的时间戳和关联的 view/exception，但没有媒体文件关联。需要在事件触发时保留录像片段用于回放。

AI 检测引擎尚未实现，但 clip 存储接口可以先建——只管存和读，不做收口。

## Goals / Non-Goals

**Goals:**
- SituationEvent 模型新增 `clip_path` 字段
- 环形缓冲区：缓存在推流管线中经过的帧（加框后或原始）
- "精彩回放"式触发：事件触发时取 (trigger - X 秒) 到 (trigger + Y 秒) 的帧写成 mp4
- clip 文件流式读取 API
- 时间轴查询 API（画面 + 时间范围 → 事件列表，含 clip_path）

**Non-Goals:**
- 不做截图（screenshot）
- 不做处置状态机（status / handler / comment）
- 不做 AI 推理收口——clip 服务的 start/stop/trigger 是公开接口，AI 引擎后续调用
- 环形缓冲区不负责帧上加框——上游给什么帧就存什么

## Decisions

### 1. 环形缓冲区：每 View 一个

**选择**: 每个 MonitorView 一个缓冲区实例，由 `ClipService.start(view_id)` 创建，`stop(view_id)` 销毁。

```
src/service/replay_module/
├── ring_buffer.py    ← 环形缓冲区 (deque + threading.Lock)
└── clip.py           ← clip 写入 (从 buffer 取帧 → ffmpeg 编码 → mp4)
```

`ring_buffer.py`:
```python
class RingBuffer:
    def __init__(self, max_seconds, fps=25):
        self._frames = deque(maxlen=max_seconds * fps)
    
    def push(self, frame_bytes: bytes) -> None
    def dump(self, from_offset_seconds: int) -> list[bytes]
```

`clip.py`:
```python
def write_clip(view_id, event_id, buffer, pre_seconds, post_seconds) -> str:
    # 1. 从 buffer dump 过去 pre_seconds 秒的帧
    # 2. 继续从 buffer 取 post_seconds 秒的新帧
    # 3. 调用 ffmpeg (stdin pipe) 编码为 mp4
    # 4. 写入 clips/event_{id}.mp4
    # 5. 返回相对路径
```

### 2. 配置

| 参数 | 默认 | 说明 |
|------|------|------|
| `CLIP_BUFFER_SECONDS` | 30 | 环形缓冲区保留最近 N 秒 |
| `CLIP_PRE_SECONDS` | 5 | 触发时回退 X 秒开始写 |
| `CLIP_POST_SECONDS` | 10 | 触发后继续录制 Y 秒 |
| `CLIP_DIR` | `./clips` | clip 存储根目录 |

### 3. clip 文件格式

**选择**: MP4 (H.264) — 直接适用于浏览器 `<video>` 标签回放。

### 4. API

```
GET  /api/v1/views/{id}/timeline   时间轴
     ?start=&end=
     返回: { events: [{id, exception_name, severity, timestamp, clip_path}] }

GET  /api/v1/events/{id}/clip      返回 clip 文件 (StreamingResponse)
```

### 5. 与 SituationEvent 的关联

`ClipService.trigger(view_id, event_id)` 流程：
1. 调 `write_clip()` 生成文件
2. 通过 `SituationEventRepo` 更新对应 event 的 `clip_path`
3. 写一条 ALERT 类型的 LogEntry（如果日志模块已就绪）

### 6. 缓冲区生命周期

```
View 创建 → ClipService.start(view_id)
View 运行 → buffer.push(frame) 每帧调用
事件触发 → ClipService.trigger(view_id, event_id) → 写 clip + 更新 event
View 删除 → ClipService.stop(view_id) → 清空 buffer
```

调用方（AI 引擎或 View 管线）负责在帧到达时调 `push()`。本次不实现调用方——只建存储层。

## Risks / Trade-offs

- **[R] 环形缓冲区内存占用**: 30 秒 × 25fps × 每帧 ~200KB(1080p JPEG) = ~150MB per View → 限制同时缓冲的 View 数量，或降低帧率/分辨率
- **[R] clip 写入期间阻塞**: trigger 调用需等待 post_seconds 秒才能返回 → 在后台线程中异步写 clip，trigger 立即返回，写完后异步更新 event.clip_path
- **[R] 没有真正的帧推流**: AI 引擎未就绪时无法测试缓冲区→ 环形缓冲区提供 mock 接口：`push_mock(frame_bytes)` 用于测试
