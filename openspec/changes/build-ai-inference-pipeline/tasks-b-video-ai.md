# Part B - Video AI

> **Owner**: ___
> **Depends on**: Part A EventBus, YOLO Detection format, and frame reader iteration.
> **Parallel strategy**: Can be developed against mocked Part A interfaces, then wired to the real frame pipeline.

## 7. ByteTrack Person Tracking

- [x] 7.1 Create `src/service/vision_module/vision_tracking/byte_tracker.py` with a `ByteTracker` wrapper and deterministic IoU fallback.
- [x] 7.2 Implement `update(detections) -> list[Track]`, where `Track = {bbox, track_id, score}`, using only YOLO person detections.
- [x] 7.3 Support configurable thresholds: `BYTETRACK_TRACK_THRESH` default `0.5`, `BYTETRACK_MATCH_THRESH` default `0.8`.
- [x] 7.4 Maintain tracker state: `IDLE` when no person boxes are present, `ACTIVE` while tracking, and return to `IDLE` after the configured lost-frame threshold.

## 8. Face Recognition

- [x] 8.1 Create `src/service/vision_module/vision_face/face_recognizer.py` with a `FaceRecognizer` class.
- [x] 8.2 Load `NamedPerson` face vectors into memory as `{128d_encoding: person_name}` style lookup data.
- [x] 8.3 Implement `recognize(frame, tracks) -> list[FaceResult]`: crop each person bbox, convert BGR to RGB, run face detection/encoding, and compare against known people.
- [x] 8.4 Use `face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_MATCH_TOLERANCE)` when the optional face library is available.
- [x] 8.5 Return `FaceResult = {track_id, person_name|None, result: NO_RESULT|STRANGER|NORMAL}`.
- [x] 8.6 Support frame skipping through `FACE_SKIP_FRAMES` default `5`, reusing the latest per-track result between recognition frames.
- [x] 8.7 Skip person crops smaller than `50x50` pixels.
- [x] 8.8 Publish face results to EventBus topic `FACE`.
- [x] 8.9 Provide `get_face_labels() -> dict[track_id, str]` for the Part A annotation layer.

## 9. SlowFast Action Recognition

- [x] 9.1 Create `src/service/vision_module/vision_slowfast/slowfast_runner.py` with a `SlowFastRunner` class.
- [x] 9.2 Maintain a per-track frame queue with `defaultdict[str, deque(maxlen=32)]`.
- [x] 9.3 Implement `enqueue(track_id, frame_crop)` so inference is triggered once the queue reaches the configured clip length.
- [x] 9.4 Keep SlowFast model loading optional/injectable so CI can test queue and publishing logic without downloading large weights.
- [x] 9.5 Support `infer_kinetics(clip_32frames) -> ActionType label + confidence` through an injectable inference callback.
- [x] 9.6 Support per-box AVA-style action labels through an injectable inference callback.
- [x] 9.7 Map action labels to the `ai-model-capability` action type set.
- [x] 9.8 Publish action results to EventBus topic `ACTION`.
- [x] 9.9 On inference exceptions, clear the affected track queue, log the failure, and allow the next full queue to retry.

## 10. Electronic Fence

- [x] 10.1 Create `src/service/vision_module/vision_fence/fence_engine.py` with a `FenceEngine` class.
- [x] 10.2 Load all `ElectronicFence` records for the active View into memory.
- [x] 10.3 Implement `check(tracks, frame_timestamp)` to compare every track bbox against every fence polygon.
- [x] 10.4 Treat `person_bbox intersect fence_polygon area > 0` as a positive overlap sample.
- [x] 10.5 Maintain a per-`(fence_id, track_id)` deque with `append((timestamp, True|False))` and expire samples older than `now - fence.dwell_time`.
- [x] 10.6 Trigger `FenceEventResult.ENTERED` when `count(True) / len(deque) >= fence.density`.
- [x] 10.7 Maintain per-`(fence_id, track_id)` state: `NOT_ENTERED -> ENTERED -> NOT_ENTERED` after the configured `leave_frames` without overlap.
- [x] 10.8 Publish fence events to EventBus topic `FENCE`.
