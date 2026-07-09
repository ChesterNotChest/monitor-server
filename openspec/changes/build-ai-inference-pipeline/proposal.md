## Why

Core monitoring pipeline (`build-core-monitoring-pipeline`) 实现了 Node WSS 连接、设备发现、View CRUD、FFmpeg 合并推 SRS。但 Server 拉取合并后的 View 流是"裸流"——没有目标检测框、没有行为标签、没有声音分类、没有人脸识别、没有禁区告警。Server 当前只能"看"但不能"识别"。

本次变更是让 Server 从"监控流媒体中枢"升级为"智能分析中枢"——在拉流和推流之间插入 AI 推理管线，四个模型并行分析音视频帧，产出统一的枚举事件列表，触发告警规则。

## What Changes

- **帧管线基础设施**：OpenCV 从 SRS 拉 RTMP 流、逐帧解码，ByteTrack 跨帧人物追踪分配 track_id
- **YOLO11 目标检测**（video 线性前置）：检出 person/车/刀/枪等 15 类实体 → 产出 EntityType 枚举事件列表
- **人脸识别**：基于 YOLO person crop → dlib 人脸检测 → 128D 特征向量比对 NamedPerson 库 → 产出 FaceRecognitionResult 枚举事件
- **SlowFast 行为识别**：基于 ByteTrack 收集的 per-person 连续帧 clip → Kinetics 场景分类 + AVA 人物动作 → 产出 ActionType 枚举事件
- **YAMNet 音频分类**：独立音频分支，YAMNet 分类 521 类 AudioSet → 映射到 SoundType 枚举 → 产出 SoundType 枚举事件
- **电子围栏**：YOLO 人形框 × 围栏多边形 = 交集检测 + 滑动窗口密度统计 → 产出 FenceEventType 枚举事件
- **标注叠加**：OpenCV 在 YOLO/人脸/行为结果上画框、标签、时间戳 → 标注帧推 FFmpeg
- **告警引擎**：ExceptionDef 规则匹配——活跃枚举事件集合覆盖规则要求 → 触发告警（SituationEvent + AlertGroup）
- **模型变更**：ElectronicFence 新增 name/view_id/dwell_time/density/leave_frames；新增 FenceEventType 枚举模型 + 表；ExceptionDef 新增 fence_event FK
- **配置扩展**：帧率、置信度阈值、dwell_time/density 默认值、ByteTrack 参数

## Capabilities

### New Capabilities

- `frame-pipeline`: OpenCV 从 SRS 拉流 + 逐帧解码 + 帧率控制，每个 View 一个独立拉流会话
- `person-tracking`: ByteTrack 跨帧人物追踪，为 YOLO person 框分配稳定 track_id
- `yolo-detection`: YOLO11n 目标检测，产出 EntityType 枚举事件列表（video 管线线性前置）
- `face-recognition-pipeline`: person crop → dlib 人脸检测 → 128D 特征比对 → FaceRecognitionResult
- `slowfast-inference`: ByteTrack per-person 帧队列 → SlowFast Kinetics + AVA 并行推理 → ActionType
- `yamnet-inference`: 独立音频分支，YAMNet AudioSet 分类 → SoundType
- `electronic-fence-logic`: IoU 交集检测 + 滑动窗口密度判定 + 状态机 → FenceEventType
- `annotation-overlay`: OpenCV 画框/标签/时间戳叠加到标注帧
- `alert-engine`: ExceptionDef 规则匹配引擎——枚举事件集合 ⊇ 规则要求 → 告警触发
- `annotated-stream-merge`: FFmpeg 合并标注 video + 原始 audio → 推 SRS 成品 View 流

### Modified Capabilities

- `electronic-fence-model`: 新增 name、view_id、dwell_time、density、leave_frames 字段
- `exception-model`: 新增 fence_event FK → FenceEventType
- `ai-model-capability`: 接入 FenceEventType 枚举事件，补全枚举事件体系

## Impact

- **新增 `src/service/ai_module/`**：frame_reader（帧读取）、byte_tracker（追踪）、yolo_detector、face_recognizer、slowfast_runner、yamnet_runner、fence_engine、annotation_overlay、alert_engine
- **新增 `src/models/fence_event_type.py`**：FenceEventType 枚举模型
- **修改 `src/models/electronic_fence.py`**：加 name、view_id、dwell_time、density、leave_frames
- **修改 `src/models/exception.py`**：加 fence_event FK
- **配置变更**：YOLO_CONFIDENCE、FPS_TARGET、DWELL_TIME_DEFAULT、DENSITY_DEFAULT、BYTETRACK_* 等
- **依赖新增**：bytetrack（跨帧追踪）、scipy（IoU 计算）
