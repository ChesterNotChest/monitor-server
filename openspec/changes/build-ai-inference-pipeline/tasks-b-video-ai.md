# Part B — 视频 AI

> **负责人**: ___
> **依赖**: Part A（EventBus + YOLO 输出的 Detection 格式 + frame_reader 帧迭代）
> **并行策略**: 可用 Part A interface 的 mock 先行开发

## 7. ByteTrack 人物追踪

- [ ] 7.1 创建 `src/service/ai_module/byte_tracker.py`：`ByteTracker` 类，封装 bytetrack 库
- [ ] 7.2 `update(detections) -> list[Track]`：`Track = {bbox, track_id, score}`，输入 YOLO person detections（仅 class_id=person）
- [ ] 7.3 配置参数：`BYTETRACK_TRACK_THRESH`（0.5）、`BYTETRACK_MATCH_THRESH`（0.8）
- [ ] 7.4 状态机：IDLE（无 person 框）→ ACTIVE（追踪中），无 person 超过 30 帧 → IDLE

## 8. 人脸识别

- [ ] 8.1 创建 `src/service/ai_module/face_recognizer.py`：`FaceRecognizer` 类
- [ ] 8.2 启动时加载所有 NamedPerson：`{128d_encoding: person_name}` 到内存
- [ ] 8.3 `recognize(frame, tracks) -> list[FaceResult]`：对每个 track 的 bbox 区域裁剪 → dlib 人脸检测 → 128D 提取 → 比对
- [ ] 8.4 比对逻辑：`face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_MATCH_TOLERANCE)`
- [ ] 8.5 `FaceResult = {track_id, person_name|None, result: NO_RESULT|STRANGER|NORMAL}`
- [ ] 8.6 跳帧：`FACE_SKIP_FRAMES`（默认 5），中间帧复用上次结果
- [ ] 8.7 最小人脸尺寸：person crop < 50×50 px 跳过
- [ ] 8.8 Publish FaceResult 到 EventBus topic `FACE`
- [ ] 8.9 提供 `get_face_labels() -> dict[track_id, str]` 供 Part A 标注层调用

## 9. SlowFast 行为识别

- [ ] 9.1 创建 `src/service/ai_module/slowfast_runner.py`：`SlowFastRunner` 类
- [ ] 9.2 Per-track_id 帧队列：`defaultdict[str, deque(maxlen=32)]`
- [ ] 9.3 `enqueue(track_id, frame_crop)` → 队列满 32 帧 → 触发推理
- [ ] 9.4 加载 Kinetics R-50 模型 + AVA R-50 模型（启动时一次性）
- [ ] 9.5 `infer_kinetics(clip_32frames)` → ActionType label + confidence
- [ ] 9.6 `infer_ava(clip_32frames + bboxes)` → per-box action labels
- [ ] 9.7 ActionType 映射（12 类，定义在 `ai-model-capability` spec）
- [ ] 9.8 Publish ActionType 到 EventBus topic `ACTION`
- [ ] 9.9 推理异常 → 清空该 track 队列，记录日志，下次满再试

## 10. 电子围栏

- [ ] 10.1 创建 `src/service/ai_module/fence_engine.py`：`FenceEngine` 类
- [ ] 10.2 启动时加载 View 下所有 `ElectronicFence` 记录到内存
- [ ] 10.3 `check(tracks, frame_timestamp)` → 对每个 track 的 bbox × 每个 fence 的 polygon 做 IoU 检测
- [ ] 10.4 IoU 算法：`person_bbox ∩ fence_polygon` 面积 > 0 → 记录 True
- [ ] 10.5 Per-`(fence_id, track_id)` deque：`append((timestamp, True|False))`，`popleft` 过期帧（`timestamp < now - fence.dwell_time`）
- [ ] 10.6 密度判定：`count(True) / len(deque) ≥ fence.density` → 触发 `FenceEventResult.ENTERED`
- [ ] 10.7 状态机 per `(fence_id, track_id)`：`NOT_ENTERED —密度达标→ ENTERED —连续 leave_frames 帧无重叠→ NOT_ENTERED`
- [ ] 10.8 Publish FenceEvent 到 EventBus topic `FENCE`
