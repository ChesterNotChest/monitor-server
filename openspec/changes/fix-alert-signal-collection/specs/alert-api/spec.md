# Alert API (delta)

## MODIFIED Requirements

### Requirement: 告警引擎枚举信号采集
系统 SHALL 使用 Pipeline 同步快照 `ActiveSignals` 作为告警匹配的数据源，替代通过 EventBus 异步订阅采集枚举信号。

AlertEngine SHALL 保留 `self._latest_signals` 引用，由 `AIPipeline._run_loop` 在每帧处理后同步更新。

`_check()` SHALL 直接从 `self._latest_signals` 读取 `entity_type_ids / action_type_ids / sound_type_ids / face_result_ids / fence_result_ids` 进行匹配。

#### Scenario: 告警引擎读取快照匹配
- **WHEN** `_check_loop` 每 5 秒触发检查
- **THEN** `_check()` 从 `self._latest_signals` 获取活跃 ID 集合，与 ExceptionDef 条件做 `issubset` 匹配

#### Scenario: 快照为空时不触发
- **WHEN** Pipeline 尚未产生任何帧（`self._latest_signals` 为 None）
- **THEN** AlertEngine `_check()` 跳过匹配，不触发异常

### Requirement: 冷却只看异常种类
系统 SHALL 使用 `(view_id, exc_id)` 二元组作为冷却和 ongoing 状态的 key。同一 View 中同一种异常触发后，在冷却时间内不再重复触发，无论是由哪个 track 引起的。

#### Scenario: 同种类不同 track 共享冷却
- **WHEN** track 3 触发异常 exc_id=1 后进入冷却，2 秒后 track 7 也匹配到 exc_id=1
- **THEN** track 7 的匹配被冷却跳过（cooldown HIT），不创建新 SituationEvent，不启动新录制

#### Scenario: 不同种类独立冷却
- **WHEN** exc_id=1 在冷却中，同时 exc_id=2 首次匹配
- **THEN** exc_id=2 正常触发新告警

## ADDED Requirements

### Requirement: AlertEngine debug 日志
系统 SHALL 在 AlertEngine 关键生命周期点输出 INFO 级别日志，便于运维验证冷却/录制行为。

日志 SHALL 包含：
- 冷却命中时：被冷却的 key `(view_id, exc_id)` 和剩余冷却时间
- 冷却重置时：key 和原因（告警结束/录制停止）
- 新告警触发时：view_id, exc_id, 触发的 track_id, recording_id
- 告警结束时：key 和原因（无活跃匹配）

#### Scenario: 冷却命中日志
- **WHEN** 同一 `(view_id, exc_id)` 在冷却时间内再次匹配
- **THEN** 日志输出 `[AlertEngine] cooldown HIT key=(1,2) remaining=15s`
