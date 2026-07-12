# Part A — 基础层

> **负责人**: ___
> **前置**: 无
> **产出**: 模型变更 + 帧管线 + YOLO + 标注合并推流 + 配置。产出 EventBus 接口供 B/C 消费。

## 1. 模型变更

- [x] 1.1 `ElectronicFence` 模型：`coords` 类型从 `Text` 改为 `JSON`；新增 `name`（String，非空）、`view_id`（FK→monitor_views，非空，索引）、`dwell_time`（Integer，默认 10）、`density`（Float，默认 0.6）、`leave_frames`（Integer，默认 5）。`coords` 固定 4 个顶点（不规则四边形），像素坐标系（与 YOLO bbox 同空间，左上角为原点），JSON 格式 `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`
- [x] 1.1b `electronic_fences` 旧表：开发阶段无数据 → `Base.metadata.drop_all` 删表 + `create_all` 重建（SQLite 不支持 ADD COLUMN 迁移）
- [x] 1.2 新增 `src/models/fence_event_type.py`：`FenceEventType(Base)` — `id`（PK）、`name`（String，unique，非空）
- [x] 1.3 `ExceptionDef` 模型新增 `fence_event_id`（FK→fence_event_types，可空，索引）
- [x] 1.4 `src/constants.py` 新增 `FenceEventResult(IntEnum)`：`ENTERED = 1`
- [x] 1.5 `src/models/__init__.py` 导入 `FenceEventType`
- [x] 1.6 `ElectronicFence.coords` 固定 4 点不规则四边形：`[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`，像素坐标系（与 YOLO bbox 同空间，左上角为原点），创建时校验点数 ≠ 4 则 422

## 2. EventBus（内存事件通道）

- [x] 2.1 创建 `src/service/vision_module/event_bus.py`：`subscribe(event_type: str, callback)`、`publish(event_type: str, payload: dict)`、`unsubscribe(event_type, callback)`
- [x] 2.2 事件类型常量：`ENTITY`、`ACTION`、`SOUND`、`FACE`、`FENCE`
- [x] 2.3 `asyncio.Lock` 保护订阅/发布并发安全
- [x] 2.4 EventBus 接口文档（供 B/C 调用）

**EventBus 接口契约（B/C 依赖）：**

```python
# 发布事件
await event_bus.publish("ENTITY", {"view_id": 1, "entities": [{"entity_type_id": 1, "bbox": [...], "confidence": 0.9}]})

# 订阅事件
async def on_entity(payload: dict): ...
event_bus.subscribe("ENTITY", on_entity)
```

## 3. 帧管线

- [x] 3.1 创建 `src/service/vision_module/frame_reader.py`：`FrameReader` 类，封装 `cv2.VideoCapture`
- [x] 3.2 `open(view_id, video_id)`：构建 RTMP URL → `VideoCapture` → 逐帧迭代
- [x] 3.3 断流重连：指数退避 1s→60s，最多连续失败 10 次后标记 ERROR
- [x] 3.4 FPS 控制：`FPS_TARGET`（默认 15），跳帧或等帧
- [x] 3.5 状态机：IDLE → ACTIVE → ERROR，`get_state()` 方法

## 4. YOLO 检测（video 线性前置）

- [x] 4.1 创建 `src/service/vision_module/yolo_detector.py`：`YoloDetector` 类
- [x] 4.2 启动时加载 `yolo11n.pt`，预热推理一次
- [x] 4.3 `detect(frame) -> list[Detection]`：`Detection = {bbox: [x1,y1,x2,y2], class_id: int, confidence: float, entity_type_id: int}`
- [x] 4.4 COCO class_id → EntityType 映射表（12 类，定义在 `ai-model-capability` spec）
- [x] 4.5 `YOLO_CONFIDENCE` 过滤（默认 0.5），低于阈值丢弃
- [x] 4.6 每帧推理后 publish 到 EventBus topic `ENTITY`
- [x] 4.7 状态机：IDLE → ACTIVE → ERROR，单帧异常 skip 不崩溃
- [x] 4.8 Add `YOLO_DEVICE` config with default `cpu`; deployment can set `YOLO_DEVICE=0` to use GPU.

## 5. 标注叠加 + 合流推 SRS

- [x] 5.1 创建 `src/service/vision_module/annotation_overlay.py`：`draw_detections(frame, detections)` → 画框（绿色 person/红色 knife 等）+ 标签文字 + 时间戳
- [x] 5.2 接口预留：`draw_face_labels(frame, face_results)` — 人脸标注（B 实现后调用）
- [x] 5.3 创建 `src/service/vision_module/stream_merger.py`：FFmpeg 子进程 `stdin` pipe 接收 rawvideo BGR24 → 编码 FLV + 拉取 raw audio RTMP → 合并推 `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/view/{view_id}`
- [x] 5.4 `start(view_id, video_id, audio_id, width, height, fps)` → 返回 FFmpeg subprocess 句柄
- [x] 5.5 `push_frame(process, frame)` → `process.stdin.write(frame.tobytes())`。帧格式为 `raw_bgr24`（numpy BGR24），与 `FrameRingBuffer` 默认格式一致——录制系统无需适配即可消费标注帧
- [x] 5.6 `stop(process)` → SIGTERM
- [x] 5.7 标注层订阅 EventBus topic `FACE`：收到 `{track_id: int, label: str}` 后在当前帧上绘制人脸标签（A 消费 B 产出，B 不直接调 A 的绘图函数）

## 6. Pipeline 调度器（模块对接协议）

- [x] 6.1 创建 `src/service/vision_module/pipeline.py`，定义数据契约
- [x] 6.2 `AIPipeline` 类骨架：`register_frame_hook`、`_process_frame`、`start`、`stop`
- [x] 6.3 主循环流程：frame_reader → YOLO → EventBus → hooks → annotation → stream_merger
- [x] 6.4 导出 `AIPipeline` 作为 B/C 的唯一入口点

## 7. 测试 Fixtures 准备

- [x] 7.1 创建 `src/tests/fixtures/download_fixtures.py`：自动下载 COCO8 + LFW/UrbanSound8K 占位
- [x] 7.2 COCO8 自动下载解压到 `src/tests/fixtures/coco8/`
- [x] 7.3 LFW/UrbanSound8K 子集 Part B/C 开发时选取，fixture 目录提供 README 占位说明
- [x] 7.4 PETS 2009 S1-L1 端到端视频 — 开发阶段用 Node 推流验证，不需要静态视频
- [x] 7.5 创建 `tests/fixtures/README.md`，记录每个 fixture 的来源、授权、用途

## 8. 配置

- [x] 8.1 `config.py` 新增全部 AI 管线配置项（FPS_TARGET/YOLO_CONFIDENCE/YOLO_MODEL_PATH 等 17 项）
- [x] 8.2 `.env` 使用默认值即可（config.py 已提供全部默认值）
- [x] 8.3 `YOLO_DEVICE` defaults to `cpu` and remains overrideable from `.env`/environment for GPU deployments.
