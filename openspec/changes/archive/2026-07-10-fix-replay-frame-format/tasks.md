## 1. RingBuffer + Recorder 帧格式

- [ ] 1.1 `FrameRingBuffer.__init__` 新增 `format` 参数（默认 `"raw_bgr24"`）
- [ ] 1.2 `RecordingSession.__init__` 接收 `format` 参数
- [ ] 1.3 `RecordingSession.start()` 按 format 分支 FFmpeg 命令
- [ ] 1.4 `RecordingSession` 构造函数从 buffer 读取 format 自动匹配
- [ ] 1.5 `replay_task.py` 的 `start_buffer()` 传入 format 参数

## 2. RecordingRepo 原生 INSERT

- [ ] 2.1 `RecordingRepo.create()` 改用 `insert(Recording).values(...)` + `db.execute()`
- [ ] 2.2 移除 `RecordingRepo` 对 ORM `self.model(**kwargs)` 的依赖

## 3. 验证

- [ ] 3.1 `test_replay_smoke.py` 用 raw BGR24 格式验证 → 产物时长 ≥ 5s
- [ ] 3.2 新增 JPEG 格式 smoke test → 产物正确播放
- [ ] 3.3 验证 `RecordingRepo.create()` 在 partial import 下不崩溃
