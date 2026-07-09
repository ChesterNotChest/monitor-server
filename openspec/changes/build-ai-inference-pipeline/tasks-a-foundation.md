# Part A — 基础层

> **负责人**: ___
> **前置**: 无
> **产出**: 模型变更 + 帧管线 + YOLO + 标注合并推流 + 配置。产出 EventBus 接口供 B/C 消费。

## 1. 模型变更

- [ ] 1.1 `ElectronicFence` 模型新增 `name`（String，非空）、`view_id`（FK→monitor_views，非空，索引）、`dwell_time`（Integer，默认 10）、`density`（Float，默认 0.6）、`leave_frames`（Integer，默认 5）
- [ ] 1.2 新增 `src/models/fence_event_type.py`：`FenceEventType(Base)` — `id`（PK）、`name`（String，unique，非空）
- [ ] 1.3 `ExceptionDef` 模型新增 `fence_event_id`（FK→fence_event_types，可空，索引）
- [ ] 1.4 `src/constants.py` 新增 `FenceEventResult(IntEnum)`：`ENTERED = 1`
- [ ] 1.5 `src/models/__init__.py` 导入 `FenceEventType`
- [ ] 1.6 `ElectronicFence.coords` 坐标规范：`[[x1,y1], [x2,y2], ...]`，像素坐标系（与 YOLO bbox 同空间），左上角为原点

## 2. EventBus（内存事件通道）

- [ ] 2.1 创建 `src/service/ai_module/event_bus.py`：`subscribe(event_type: str, callback)`、`publish(event_type: str, payload: dict)`、`unsubscribe(event_type, callback)`
- [ ] 2.2 事件类型常量：`ENTITY`、`ACTION`、`SOUND`、`FACE`、`FENCE`
- [ ] 2.3 `asyncio.Lock` 保护订阅/发布并发安全
- [ ] 2.4 EventBus 接口文档（供 B/C 调用）

**EventBus 接口契约（B/C 依赖）：**

```python
# 发布事件
await event_bus.publish("ENTITY", {"view_id": 1, "entities": [{"entity_type_id": 1, "bbox": [...], "confidence": 0.9}]})

# 订阅事件
async def on_entity(payload: dict): ...
event_bus.subscribe("ENTITY", on_entity)
```

## 3. 帧管线

- [ ] 3.1 创建 `src/service/ai_module/frame_reader.py`：`FrameReader` 类，封装 `cv2.VideoCapture`
- [ ] 3.2 `open(view_id, video_id)`：构建 RTMP URL → `VideoCapture` → 逐帧迭代
- [ ] 3.3 断流重连：指数退避 1s→60s，最多连续失败 10 次后标记 ERROR
- [ ] 3.4 FPS 控制：`FPS_TARGET`（默认 15），跳帧或等帧
- [ ] 3.5 状态机：IDLE → ACTIVE → ERROR，`get_state()` 方法

## 4. YOLO 检测（video 线性前置）

- [ ] 4.1 创建 `src/service/ai_module/yolo_detector.py`：`YoloDetector` 类
- [ ] 4.2 启动时加载 `yolo11n.pt`，预热推理一次
- [ ] 4.3 `detect(frame) -> list[Detection]`：`Detection = {bbox: [x1,y1,x2,y2], class_id: int, confidence: float, entity_type_id: int}`
- [ ] 4.4 COCO class_id → EntityType 映射表（15 类，定义在 `ai-model-capability` spec）
- [ ] 4.5 `YOLO_CONFIDENCE` 过滤（默认 0.5），低于阈值丢弃
- [ ] 4.6 每帧推理后 publish 到 EventBus topic `ENTITY`
- [ ] 4.7 状态机：IDLE → ACTIVE → ERROR，单帧异常 skip 不崩溃

## 5. 标注叠加 + 合流推 SRS

- [ ] 5.1 创建 `src/service/ai_module/annotation_overlay.py`：`draw_detections(frame, detections)` → 画框（绿色 person/红色 knife 等）+ 标签文字 + 时间戳
- [ ] 5.2 接口预留：`draw_face_labels(frame, face_results)` — 人脸标注（B 实现后调用）
- [ ] 5.3 创建 `src/service/ai_module/stream_merger.py`：FFmpeg 子进程 `stdin` pipe 接收 rawvideo BGR24 → 编码 FLV + 拉取 raw audio RTMP → 合并推 `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/view/{view_id}`
- [ ] 5.4 `start(view_id, video_id, audio_id, width, height, fps)` → 返回 FFmpeg subprocess 句柄
- [ ] 5.5 `push_frame(process, frame)` → `process.stdin.write(frame.tobytes())`
- [ ] 5.6 `stop(process)` → SIGTERM

## 6. 配置

- [ ] 6.1 `config.py` 新增：`FPS_TARGET`（15）、`YOLO_CONFIDENCE`（0.5）、`YOLO_MODEL_PATH`（`src/third-party/yolo/yolo11n.pt`）、`STREAM_RECONNECT_MAX_RETRIES`（10）
- [ ] 6.2 `.env` 添加默认值
