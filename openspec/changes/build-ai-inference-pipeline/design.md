## Context

Server 已有 View 合并推流能力（`build-core-monitoring-pipeline`），AI 推理管线在拉流和推流之间插入。当前 `explore_ai_pipeline.md` 已画出完整数据通路，`ai-model-capability` spec 已定义四模型枚举映射。本次设计聚焦工程实现：帧管线、模块状态机、标注叠加、告警引擎。

## Goals / Non-Goals

**Goals:**
- OpenCV 从 SRS 拉取 View 的 raw video 流，逐帧解码
- ByteTrack 为 YOLO person 框分配稳定 track_id（视频管线基础）
- YOLO11n 目标检测 → EntityType 事件（线性前置，其他视频模块依赖 YOLO 框）
- face_recognition / SlowFast / YAMNet / 电子围栏 四个模块并行
- 每个模块产出"枚举事件列表"，写入 EventBus
- 告警引擎按 ExceptionDef 规则匹配 EventBus → 触发告警
- OpenCV 标注叠加在 YOLO/人脸结果上 → 标注帧推 FFmpeg merge
- 每个模块自带状态机，异常时记录日志不崩溃
- 模型变更：ElectronicFence 加字段、新增 FenceEventType、ExceptionDef 加 FK

**Non-Goals:**
- GPU 优化（首版 CPU 推理）
- YOLO 微调（使用预训练 COCO 权重）
- SlowFast 模型训练
- 录像回放（已有 `build-clip-replay` change）
- 实时告警推送 WebSocket（本次只写 DB）

## Architecture

### 管线拓扑

```
SRS (raw video)                 SRS (raw audio)
    │                                │
    ▼                                │
OpenCV VideoCapture                  │
    │                                │
    ▼                                │
YOLO11 检测 ──▶ EntityType 事件 ──┐  │
    │                              │  │
    ├─ person boxes ──▶ ByteTrack  │  │
    │       │                      │  │
    │    track_id                  │  │
    │       │                      │  │
    ├───────┼──▶ Face Recognition  │  │
    │       │    → FaceResult 事件  │  │
    │       │                      │  │
    ├───────┼──▶ SlowFast Queues   │  │
    │       │    → ActionType 事件  │  │
    │       │                      │  │
    ├───────┼──▶ Fence Engine      │  │
    │       │    → FenceEvent 事件  │  │
    │       │                      │  │
    │       │                      │  │
    └───────┼──▶ Annotation        │  │
            │   (画框/标签)         │  │
            │                      │  │
            ▼                      ▼  ▼
    标注帧 ──────▶ EventBus ──▶ AlertEngine
            │           │
            │     ExceptionDef 匹配
            │     → SituationEvent
            │     → AlertGroup
            │
            ▼
FFmpeg merge (标注 video + audio) → SRS (View 成品流)
```

### 模块状态机

每个模块统一三态：

```
    ┌────────┐      启动      ┌────────┐     异常/EOF    ┌────────┐
    │  IDLE  │ ──────────────▶│ACTIVE  │ ──────────────▶│ ERROR  │
    └────────┘                └────────┘                └────────┘
                                   │                        │
                                   │ 正常处理                │ 记录日志
                                   ▼                        │ 不崩溃
                              产出事件                      │
                                                            ▼
                                                    恢复/重建连接
                                                       │
                                                       ▼
                                                     ACTIVE
```

差异：
- **YOLO**：IDLE → (首帧解码成功) → ACTIVE。ERROR 时跳过当前帧继续。
- **SlowFast**：IDLE → (首个人物 clip 满 T 帧) → ACTIVE。ERROR 时清空队列继续。
- **YAMNet**：IDLE → (音频流首段到达) → ACTIVE。ERROR 时重新拉流。
- **Face**：IDLE → (首次检测到人脸) → ACTIVE。ERROR 时跳过当前 person。
- **Fence**：IDLE → (首次接收到 YOLO person 框) → ACTIVE。ERROR 时清空该 track 队列。

### EventBus

内存中的发布/订阅通道。每个模块产出事件列表后调用 `event_bus.publish(event_type, payload)`。告警引擎订阅所有事件类型，按 ExceptionDef 规则匹配。

```python
event_bus = EventBus()
event_bus.subscribe("EntityType", alert_engine.on_entity)
event_bus.subscribe("ActionType", alert_engine.on_action)
event_bus.subscribe("SoundType", alert_engine.on_sound)
event_bus.subscribe("FaceResult", alert_engine.on_face)
event_bus.subscribe("FenceEvent", alert_engine.on_fence)
```

### 标注叠加策略

只叠加在 YOLO person 和 face recognition 结果上。SlowFast 和 SoundType 结果不入帧（写入 DB 即可）。Frame 标注后推 FFmpeg merge，与音频合并推 SRS。

## Decisions

### 1. YOLO 作为 video 管线线性前置

YOLO 产出 person boxes 后，ByteTrack 分配 track_id。Face、SlowFast、Fence 都依赖 `(frame, person_boxes, track_ids)` 三元组。如果 YOLO 崩溃，下游全部不工作——这是设计约束。

### 2. 各模块并行，事件写入 EventBus

Face / SlowFast / YAMNet / Fence 无相互依赖，并行运行。各自产出枚举事件后 publish 到 EventBus。告警引擎是唯一的消费者。

### 3. SlowFast 双模型共享同一帧队列

Kinetics 和 AVA 共用 ByteTrack per-person 帧队列。队列满 32 帧时分别送两个模型推理，结果合并为一个 ActionType 事件。

### 4. 电子围栏时间窗口用 collections.deque

每个 `(fence_id, track_id)` 维护一个 deque，append 新帧结果，popleft 过期帧。密度判定在每次 append 后同步执行。

### 5. 音频独立分支

YAMNet 不走 YOLO 和 OpenCV 视频管线。直接从 SRS 拉音频流（FFmpeg 解音频 → numpy array），每 0.96s 推理一次。产出的 SoundType 事件和其他视频事件在 EventBus 汇合。

## Acceptance Criteria

### Stage 1: 帧管线 + YOLO

- [ ] OpenCV 从 SRS 成功拉取 RTMP 视频流，逐帧解码无卡顿
- [ ] YOLO11n 每帧推理正确产出 `[{bbox, class_id, confidence}, ...]`
- [ ] EntityType 枚举事件正确写入 EventBus
- [ ] 帧率 ≥ 10fps（CPU 模式）

### Stage 2: ByteTrack + 人脸识别

- [ ] ByteTrack 为连续帧的同一 person 分配稳定 track_id
- [ ] person crop → dlib 人脸检测 → 128D 特征提取正常
- [ ] NamedPerson 库比对输出 FaceResult 枚举事件
- [ ] 陌生人识别正确标注

### Stage 3: SlowFast + YAMNet（可并行）

- [ ] Per-person 32 帧队列满时送 SlowFast Kinetics + AVA
- [ ] ActionType 枚举事件正确产出（跌倒/打架/抽烟等）
- [ ] YAMNet 音频分类正确产出 SoundType 枚举事件
- [ ] 队列满 FIFO 丢旧帧策略正确

### Stage 4: 电子围栏

- [ ] IoU person_bbox ∩ fence_polygon 正确判定
- [ ] 滑动窗口密度统计：True 占比 ≥ density → ENTERED
- [ ] 离开后状态重置正确
- [ ] FenceEventType 枚举事件正确产出

### Stage 5: 标注叠加 + 推流

- [ ] OpenCV 标注正确绘制在帧上
- [ ] 标注帧 + 原始音频 FFmpeg merge 成功推 SRS
- [ ] SRS 成品 View 流可被前端正常播放

### Stage 6: 告警引擎

- [ ] ExceptionDef 规则匹配正确（AND 逻辑——全部条件满足才触发）
- [ ] 去重：`(view_id, exception_def_id, 5s_window)` 正确去重
- [ ] SituationEvent + AlertGroup 正确写入 DB

## Risks / Trade-offs

- **YOLO 单点故障**：YOLO 崩溃 → 标注无框 + 下游全停 → 标注帧退化为原始帧继续推流
- **SlowFast 32 帧缓冲延迟**：~2 秒延迟 → 监控场景可接受，优先实时性用 FIFO 丢旧帧
- **CPU 推理吞吐**：单路 View ~10fps 有效处理速率 → 多路 View 需要 GPU 或降低帧率
- **EventBus 无持久化**：Server 重启丢失未消费事件 → 可接受，事件写入 DB 后才标记已消费

## Open Questions

- ByteTrack 参数调优（track_thresh, match_thresh）→ 实现时通过测试视频调参
- YAMNet 是独立进程还是主进程内协程 → 先主进程内协程
- 多路 View 时的 GPU 显存管理 → 首版只支持单路 View
