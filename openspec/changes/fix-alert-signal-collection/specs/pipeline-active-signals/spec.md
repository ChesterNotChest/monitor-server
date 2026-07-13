# Pipeline Active Signals

**Purpose:** Pipeline 每帧从 AI 检测结果中提取整数 ID 集合，作为 AlertEngine 告警匹配的单一数据源。

## ADDED Requirements

### Requirement: ActiveSignals 数据结构
系统 SHALL 定义 `ActiveSignals` 数据类，包含 5 个展平的整数集合字段：

- `entity_type_ids: set[int]` — 当前帧 YOLO 检测到的 `YOLOEntityType` 值
- `action_type_ids: set[int]` — 当前帧 SlowFast 识别到的 `SlowFastActionType` 值
- `sound_type_ids: set[int]` — 最近 TTL 内 YAMNet 匹配到的 `YAMNetSoundType` 值
- `face_result_ids: set[int]` — 当前帧人脸结果：`{2}`（Stranger）或空集
- `fence_result_ids: set[int]` — 当前帧围栏结果：`{1}`（ENTERED，有人进入围栏）或空集

#### Scenario: 正常帧提取所有信号
- **WHEN** 一帧处理完毕，YOLO 检测到 Person(1)+Knife(12)，SlowFast 识别到 Fighting(4)，无人脸/围栏/声音
- **THEN** ActiveSignals 为 `entity_type_ids={1,12} action_type_ids={4} sound_type_ids=∅ face_result_ids=∅ fence_result_ids=∅`

#### Scenario: Stranger 被检测
- **WHEN** 一帧中有 track_id 3 的人脸被识别为 Stranger
- **THEN** `face_result_ids = {2}`（FaceRecognitionResult.STRANGER）

#### Scenario: 有人进入围栏
- **WHEN** 一帧中有任意 track 检测到围栏进入事件
- **THEN** `fence_result_ids = {1}`（FenceEventResult.ENTERED）

### Requirement: 全局 ID 缓存
系统 SHALL 提供模块级全局变量 `_active_action_type_ids: set[int]` 和 `_active_sound_type_ids: set[int]`，由 AI 模块在产出检测结果时同步更新。

- `_active_action_type_ids` SHALL 在每帧 `process_frame()` 开始时清空，由 SlowFast 结果收集时填充
- `_active_sound_type_ids` SHALL 跨帧保留，附带 TTL（默认 5 秒），由 YAMNet SOUND_TYPE_MAP 兼容路径填充

#### Scenario: 动作 ID 缓存每帧重置
- **WHEN** VideoAIProcessor.process_frame() 开始处理新帧
- **THEN** `_active_action_type_ids` 被清空为 `set()`

#### Scenario: 声音 ID 缓存跨帧保留
- **WHEN** YAMNet 检测到 GUNSHOT（sound_type_val=1）且距上次更新不到 5 秒
- **THEN** `_active_sound_type_ids` 中包含 `1`

#### Scenario: 声音 ID 缓存 TTL 过期
- **WHEN** 距上次 YAMNet 检测到任何声音超过 5 秒
- **THEN** `_active_sound_type_ids` 被清空为 `set()`

### Requirement: Pipeline 提取快照
系统 SHALL 在 `AIPipeline._run_loop` 中，`_enrich_detection_labels()` 执行后、draw/push 之前，提取 `ActiveSignals` 并同步传给 AlertEngine。

#### Scenario: 快照传递给 AlertEngine
- **WHEN** 一帧处理完毕进入提取阶段
- **THEN** Pipeline 调用 `alert_engine.feed(signals)` 同步赋值最新快照

### Requirement: AlertEngine 从快照读取
系统 SHALL 修改 `AlertEngine._check()` 从 `self._latest_signals` 读取枚举信号，替代当前从 EventBus pool 收集 ID 的逻辑。

#### Scenario: 匹配时使用快照数据
- **WHEN** `_check_loop` 触发匹配检查
- **THEN** AlertEngine 使用 `self._latest_signals` 中的 ID 集合与 ExceptionDef 条件做 `issubset` 匹配
