## Context

AI 管线文档 §8 定义了缓存区与触发录制的完整方案。`MonitorView.cache_path` 字段已存在，指向录制文件的存储根目录。环形缓冲区和持续录制引擎需要从零搭建。

AI 检测引擎尚未实现，但录制服务的接口先建好——只管存和读，不做 AI 推理收口。

## Goals / Non-Goals

**Goals:**
- 环形缓冲区：存加框前原始帧，支持配置缓存时长
- 持续录制：告警触发开始 → 持续写帧 → 静默超时停止 → 写 flv 文件
- Recording 记录表：view_id, file_path, start_time, end_time
- 回放查询 API：按 view + 时间范围找录制文件 + 流式读取

**Non-Goals:**
- 不做截图
- 不做处置状态机
- 不修改 SituationEvent
- 不做 AI 推理收口——`alert_triggered(view_id)` 是公开接口，AI 引擎后续调用
- 不做存储清理策略（后续加）

## Decisions

### 1. 持续录制 vs 离散 clip

**选择**: 持续录制模式——告警触发开始录制，每次新告警重置静默计时器，连续 `RECORD_STOP_SILENCE_SECONDS` 秒无告警则停止。

**理由**: AI 文档 §8 明确定义。多告警密集触发时合并为一段连续录像，比每个事件一个离散 clip 更合理。

```
时间线:
  ├──[30s 缓冲区]──┤
                   ├─ 告警触发 ──────────────────────────────┤
                   │  开始录制                                  │
                   │           ├─ 新告警 ─┤                    │
                   │           │  重置计时器│                   │
                   │           │          └── 连续 60s 无告警 ──┤
                   │           │                                │
                   ├───────────■────────────────────────────────┤
                               ↑                                ↑
                           录制开始                          录制停止 → 写 flv
```

### 2. 缓冲区内容：加框前原始帧

**选择**: 环形缓冲区存储 AI 标注**之前**的原始帧（或已解码的 raw frame）。录制文件为原始画面，不含 AI 标注框。

**理由**: AI 文档 §8："保存最近 N 秒的加框前原始帧"。前端直播看的是标注画面，证据留存用的是原始画面。

### 3. 文件格式：FLV

**选择**: 录制文件使用 FLV 封装，H.264 编码。文件名 `view_{id}_{timestamp}.flv`，存储在 `{MonitorView.cache_path}/` 下。

**理由**: AI 文档 §8 明确定义。FLV 是监控场景的成熟格式（SRS 原生支持），写入过程中断也不会导致整个文件损坏（与 MP4 不同）。

### 4. Recording 记录表

**选择**: 新增 `Recording` 模型记录每次录制会话，与 `SituationEvent` 解耦。

```python
class Recording(Base):
    id, view_id, file_path, start_time, end_time, created_at
```

多告警可能对应同一段录像——通过时间范围关联，而非 FK。

### 5. 录制引擎接口

```python
# replay_task.py — 供 AI 告警引擎调用的公开接口

def start_buffer(view_id: int) -> None
    # View 创建时调用，初始化环形缓冲区

def stop_buffer(view_id: int) -> None
    # View 删除时调用，清理资源

def push_frame(view_id: int, frame_bytes: bytes) -> None
    # AI 管线每帧调用，写入缓冲区

def alert_triggered(view_id: int) -> None
    # 告警引擎触发时调用。首次调用开始录制，后续调用重置静默计时器。
    # 录制停止时自动写 flv 文件 + 写 Recording 记录。

def get_recordings(view_id: int, start, end) -> list[Recording]
    # 回放查询
```

### 6. API

```
GET /api/v1/views/{id}/recordings?start=&end=
    返回 [{id, file_path, start_time, end_time}]

GET /api/v1/recordings/{id}/stream
    流式返回 flv 文件 (StreamingResponse)
```

## Risks / Trade-offs

- **[R] 环形缓冲区内存占用**: 30s × 25fps × ~200KB/帧(1080p JPEG) ≈ 150MB/view → 限制同时缓冲的 View 数量；后续可降分辨率或改为帧索引+共享内存
- **[R] 录制期间服务重启**: 当前帧 buffer 在内存中，重启丢失 → RecordingSession 记录"录制中"状态到 Recording 表（status=recording），重启后标记为 interrupted 并写已有数据
- **[R] 多 View 并发**: 每个 View 独立缓冲区，内存线性增长 → 限制最大 View 数量
