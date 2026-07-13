## 1. 告警去重（track_id）

- [x] 1.1 `engine.py` — 去重key改为 `(view_id, exception_id, track_id)`
- [x] 1.2 `engine.py` — `_trigger` 从事件payload提取 `track_id`，无则用 -1
- [x] 1.3 `engine.py` — SituationEvent + WSS广播包含 `track_id`

## 2. 可配置冷却时间

- [x] 2.1 `exception.py` — 新增 `cooldown_seconds` 列（INTEGER, default 30）
- [x] 2.2 `exception_schema.py` — ExceptionDef schema 新增字段
- [x] 2.3 `engine.py` — 冷却时间优先读取 `exc.cooldown_seconds`，回退全局默认
- [x] 2.4 前端 `ExceptionSettings` — 新增冷却时间输入（添加/编辑/详情）

## 3. 录制回放修复

- [x] 3.1 `engine.py` — 首次告警触发后发布 `RECORDING` 事件（action: "start"）
- [x] 3.2 `vision_task.py` — `_on_recording` 处理 `start` action
- [x] 3.3 `recorder.py` + `replay_task.py` — 录制停止时回填 `SituationEvent.recording_id`
- [x] 3.4 `engine.py` — WSS广播和SituationEvent包含 `recording_id`

## 4. 端到端验证

- [ ] 4.1 创建View → 人员进入 → 确认告警触发 + 录制开始
- [ ] 4.2 前端查看回放 → 播放录制的10秒视频
- [ ] 4.3 同track冷却期内不重复告警
