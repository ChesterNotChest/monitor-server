## 1. 告警去重（track_id）

- [ ] 1.1 `engine.py` — 去重key改为 `(view_id, exception_id, track_id)`
- [ ] 1.2 `engine.py` — `_trigger` 从事件payload提取 `track_id`，无则用 -1
- [ ] 1.3 `engine.py` — SituationEvent + WSS广播包含 `track_id`

## 2. 可配置冷却时间

- [ ] 2.1 `exception.py` — 新增 `cooldown_seconds` 列（INTEGER, default 30）
- [ ] 2.2 `fence_schema.py` — ExceptionDef schema 新增字段
- [ ] 2.3 `engine.py` — 冷却时间优先读取 `exc.cooldown_seconds`，回退全局默认
- [ ] 2.4 前端 `FenceEditor` — 异常规则表单新增冷却时间输入

## 3. 录制回放修复

- [ ] 3.1 `engine.py` — 首次告警触发后发布 `RECORDING` 事件（action: "start"）
- [ ] 3.2 `vision_task.py` — `_on_recording` 处理 `start` action，调用 `replay_task.alert_triggered()`
- [ ] 3.3 `replay_task.py` — `alert_triggered` 回填 `SituationEvent.recording_id`
- [ ] 3.4 `engine.py` — WSS广播和SituationEvent包含 `recording_id`

## 4. 端到端验证

- [ ] 4.1 创建View → 人员进入 → 确认告警触发 + 录制开始
- [ ] 4.2 前端查看回放 → 播放录制的10秒视频
- [ ] 4.3 同track冷却期内不重复告警
