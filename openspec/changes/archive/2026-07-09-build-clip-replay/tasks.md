## 1. 配置

- [x] 1.1 更新 `src/config.py`：新增 `CACHE_DURATION_SECONDS`(30)、`RECORD_STOP_SILENCE_SECONDS`(60)

## 2. Recording 模型

- [x] 2.1 新建 `src/models/recording.py`：Recording 模型（id, view_id FK, file_path, start_time, end_time, created_at）
- [x] 2.2 新建 `src/repository/recording_repo.py`：按 view_id + 时间范围查询
- [x] 2.3 更新 `src/models/__init__.py` 导入 Recording

## 3. 环形缓冲区

- [x] 3.1 新建 `src/service/replay_module/__init__.py`
- [x] 3.2 新建 `src/service/replay_module/ring_buffer.py`：`FrameRingBuffer` 类
  - `__init__(max_seconds, fps=25)` — deque + threading.Lock，容量 = max_seconds * fps
  - `push(frame_bytes)` — 入队，溢出自动 drop 旧帧
  - `dump_all()` — 返回当前全部帧列表（用于录制开始时的历史帧回填）
  - `clear()` — 清空

## 4. 录制引擎

- [x] 4.1 新建 `src/service/replay_module/recorder.py`：`RecordingSession` 类
  - `__init__(view_id, buffer, cache_path)` — 绑定 buffer + 存储路径
  - `start()` — 从 buffer dump 历史帧 → 开始写入临时文件
  - `on_new_alert()` — 重置静默计时器
  - `_check_silence()` — 后台线程检查静默超时 → `stop()`
  - `stop()` — flush 剩余帧 → 关闭 ffmpeg pipe → 写 flv 文件 → 创建 Recording 记录 → 返回 file_path
  - 使用 ffmpeg stdin pipe: `ffmpeg -f rawvideo -pix_fmt bgr24 -s WxH -r fps -i pipe:0 -c:v libx264 -f flv <output.flv>`

## 5. 录制服务门户

- [x] 5.1 新建 `src/service/replay_task.py`：
  - `_buffers: dict[int, FrameRingBuffer]` — view_id → buffer 映射
  - `_sessions: dict[int, RecordingSession]` — view_id → session 映射
  - `start_buffer(view_id)` — 创建 FrameRingBuffer 实例
  - `stop_buffer(view_id)` — 清理 buffer + session
  - `push_frame(view_id, frame_bytes)` — 委托 buffer.push
  - `alert_triggered(view_id)` — 无 session → 创建 + start；有 session → on_new_alert
  - `get_recordings(view_id, start, end)` — 委托 recording_repo 查询

## 6. API

- [x] 6.1 新建 `src/schema/http/replay.py`：`RecordingResponse`（id, view_id, file_path, start_time, end_time）
- [x] 6.2 新建 `src/network/api/replay.py`：
  - `GET /api/v1/views/{id}/recordings?start=&end=` — 查询录制列表
  - `GET /api/v1/recordings/{id}/stream` — 流式返回 flv 文件
- [x] 6.3 更新 `src/network/api/__init__.py` 注册 replay_router

## 7. 测试

- [x] 7.1 新建 `src/tests/service/test_ring_buffer.py`：测试 push/dump_all/overflow/clear
- [x] 7.2 新建 `src/tests/service/test_recorder.py`：测试 RecordingSession 生命周期（start/on_new_alert/stop）
- [x] 7.3 新建 `src/tests/api/test_replay_api.py`：测试 recording 查询 + stream 端点
- [x] 7.4 运行测试：`pytest src/tests/ -v`

## 8. 验证

- [ ] 8.1 启动应用，通过 `/docs` 验证 replay 端点可用
- [ ] 8.2 模拟 `alert_triggered` → 验证 flv 文件生成 + Recording 记录写入
