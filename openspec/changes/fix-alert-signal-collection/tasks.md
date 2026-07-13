## 1. 数据结构与全局缓存

- [x] 1.1 在 `vision_annotation.py` 中新增 `ActiveSignals` dataclass 和全局变量 `_active_action_type_ids: set[int]`、`_active_sound_type_ids: set[int]`、`_active_sound_ids_updated_at: float`
- [x] 1.2 实现 `get_active_signals(view_id)` 函数：从当前帧数据 + 全局缓存中提取 ActiveSignals 快照

## 2. AI 模块写入整数 ID

- [x] 2.1 修改 `VideoAIProcessor.process_frame()`：每帧开始时清空 `_active_action_type_ids`；`collect_results()` 后用 `r.action_type_id` 填充 `_active_action_type_ids`
- [x] 2.2 修改 `YamnetRunner._classify()`：SOUND_TYPE_MAP 兼容路径发布时同步更新 `_active_sound_type_ids` 和时间戳
- [x] 2.3 修改 `AIPipeline._run_loop`：在 `_enrich_detection_labels()` 后调用 `get_active_signals()` 提取快照；将快照传给 AlertEngine

## 3. AlertEngine 数据源切换

- [x] 3.1 在 `AlertEngine` 新增 `feed(signals: ActiveSignals)` 方法和 `self._latest_signals` 属性
- [x] 3.2 修改 `AlertEngine._check()`：从 `self._latest_signals` 读取 ID 集合，去掉 EventBus pool 收集逻辑（`_cids` 调用替换为直接读 `_latest_signals` 字段）
- [x] 3.3 简化冷却 key：`_triggered` 和 `_ongoing` 的 key 从 `(view_id, exc_id, track_id)` 改为 `(view_id, exc_id)` 二元组；`_ft()` 仅用于 SituationEvent 创建时记录 track_id，不参与冷却判定
- [x] 3.4 保留 EventBus RECORDING topic 订阅（录制控制信号仍走 EventBus）或改为同步调用
- [x] 3.5 修改 `vision_task.py`：Pipeline 持有 AlertEngine 引用，在 `_run_loop` 中每帧调用 `alert_engine.feed(signals)`

## 4. SEED 补齐

- [x] 4.1 修改 `seed_alerts()`：全量写入 12 个 EntityType、16 个 ActionType、15 个 SoundType
- [x] 4.2 新增 seed：3 个 FaceRecognitionResult 和 1 个 FenceEventResult（如果数据库有对应表）
- [x] 4.3 验证种子的 idempotent 行为：重复调用不重复插入

## 5. Debug 日志

- [x] 5.1 AlertEngine 冷却命中日志：`[AlertEngine] cooldown HIT key=(v,e) remaining=Xs`
- [x] 5.2 AlertEngine 冷却重置日志：`[AlertEngine] cooldown RESET key=(v,e)`
- [x] 5.3 AlertEngine 新告警日志增强：已有 `logger.info("Alert: view=%d exc=%d id=%d track=%d rec=%s")` — 确认保留并补齐缺失字段
- [x] 5.4 AlertEngine 告警结束日志：`[AlertEngine] END key=(v,e)`
- [x] 5.5 RecordingSession 录制启动日志：`[Replay] START view=X rec=Y max_dur=Zs wind_down=Ws`
- [x] 5.6 RecordingSession keep_alive 日志：`[Replay] KEEP_ALIVE view=X rec=Y`
- [x] 5.7 RecordingSession wind_down 开始日志：`[Replay] WIND_DOWN view=X rec=Y wait=Zs`
- [x] 5.8 RecordingSession wind_down 停止日志：`[Replay] WIND_DOWN stop view=X rec=Y total=Zs`
- [x] 5.9 RecordingSession max_duration 停止日志：`[Replay] MAX_DUR stop view=X rec=Y elapsed=Zs`
- [x] 5.10 `_check()` 激活信号汇总日志：`[AlertEngine] signals E={...} A={...} S={...} F={...} FE={...}`

## 6. 回归验证

- [x] 6.1 确认 FLV 录制功能正常：告警触发 → SRS 拉流开始 → FLV 文件生成 → wind_down 超时停止
- [x] 6.2 确认录制生命周期参数传递正确：`max_recording_seconds`、`wind_down_seconds` 从 ExceptionDef 正确传至 RecordingSession
- [x] 6.3 确认冷却时间配置 API 正常：`GET/POST/PUT /api/v1/exceptions` 返回/接受 `cooldown_seconds`、`max_recording_seconds`、`wind_down_seconds` 字段
- [x] 6.4 运行已有测试 `test_alert_engine_unit.py` 确认匹配逻辑不退化
