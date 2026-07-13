## Context

当前 AlertEngine 通过 EventBus 异步订阅 5 种 AI 检测事件来采集枚举信号。但各模块发布的 payload 格式与 AlertEngine `_cids` 方法期望的 key 不一致：

| 模块 | publish key | AlertEngine 查找 key | 结果 |
|------|------------|---------------------|------|
| YOLO | `entity_type_ids` | `entity_type_ids` | ✅ 已修复（yuyu） |
| SlowFast | `actions` (dict 列表) | `action_type_ids` | ❌ 不存在 |
| YAMNet 新版 | `sound_name` (string) | `sound_type_ids` | ❌ 不存在 |
| YAMNet 旧版 | `sound_type_ids` | `sound_type_ids` | ✅ 已修复（yuyu） |
| Face | `faces` (dict 列表) | `face_result_ids` | ❌ 不存在 |
| Fence | `fences` (dict 列表) | `fence_event_ids` | ❌ 不存在 |

同时，Pipeline 绘制阶段的 `_enrich_detection_labels()` 已经正确汇总了所有检测信息，AlertEngine 重复采集且数据链断裂。

另外，EventBus 存在已知可靠性问题（[vision_annotation.py:76-87](monitor-server/src/service/vision_module/vision_annotation.py#L76-L87)）：`create_task(fire-and-forget)` 创建的订阅任务有时静默失败。

## Goals / Non-Goals

**Goals:**
- 告警引擎能正确匹配所有 5 种枚举信号（ENTITY/ACTION/SOUND/FACE/FENCE）
- 绘制阶段汇总信息和 AlertEngine 枚举采集使用同一份数据源
- 录制生命周期关键事件有 debug 日志可追踪
- FLV 录制能力不受影响（SRS 拉流 → FLV copy 逻辑不变）
- SEED 数据补齐所有枚举类型

**Non-Goals:**
- 不改 EventBus 机制（保留用于其他订阅者，如 WSS 推送）
- 不改 per-track 精度匹配（存在性告警即可）
- 不改录制核心逻辑（max_duration + wind_down + cooldown 机制保持）

## Decisions

### D1: ActiveSignals 快照 — Pipeline 同步馈送

```
当前:  各模块 → EventBus (异步) → AlertEngine._pool → _check()
改为:  各模块 → 全局 ID 缓存 (同步) → Pipeline 提取 ActiveSignals
              → AlertEngine._latest_signals ← 同步赋值
              → _check_loop() 读取最新快照
```

**理由**: 绘制阶段已经汇总了所有信息，不需要重复采集。同步赋值比 EventBus 可靠：
- 不丢事件
- 不依赖 asyncio task 生命周期
- 同一个 frame 内的检测结果原子一致

**替代方案**: 修 EventBus payload key → 仍存在异步可靠性问题和重复采集

### D2: 存在性信号 — 展平集合

```python
@dataclass
class ActiveSignals:
    entity_type_ids: set[int]    # 当前帧检测到的所有 YOLOEntityType
    action_type_ids: set[int]    # 当前帧识别到的所有 SlowFastActionType
    sound_type_ids: set[int]     # 最近 TTL 内的所有 YAMNetSoundType
    face_result_ids: set[int]    # 当前帧的人脸结果 {2}=Stranger 或空
    fence_result_ids: set[int]   # 当前帧的围栏结果 {1}=ENTERED 或空
```

不需要 `_by_track` 映射，因为用户只需要"画面里有没有XX"的存在性告警。

**理由**: 简化数据结构和匹配逻辑。per-track 精度可以通过回放视频确认。

### D3: Face → 只关注 Stranger

`_face_labels` 中有 `{track_id → "Stranger" | "张三"}` → 只要有 "Stranger" 就设 `face_result_ids = {2}`（`FaceRecognitionResult.STRANGER`）。命名人物不需要告警。

### D4: Fence → 只关注 ENTERED

`_fence_labels` 非空 → `fence_result_ids = {1}`（`FenceEventResult.ENTERED`）。不区分具体是哪个围栏。

### D5: Sound → 只走 SOUND_TYPE_MAP 兼容路径

新版危险声音检测（`_DANGER_STANDALONE` + `_COMBOS`）产出的 `sound_name` 字符串无法映射到 `YAMNetSoundType`，仅用于画面 overlay 显示。AlertEngine 只用 SOUND_TYPE_MAP 兼容路径产出的 `sound_type_ids`。

### D6: 全局 ID 缓存生命周期

- `_active_action_type_ids`: 每帧重置（`VideoAIProcessor.process_frame` 开始时清空）
- `_active_sound_type_ids`: 跨帧保留 + TTL 过期（声音持久数秒）

**理由**: 动作检测是逐帧的（每帧可能不同），声音检测结果是跨帧持续的（一次枪声持续几秒）。

### D7: SEED 全量对齐 constants.py

`seed_alerts()` 当前只写入了 4 entity / 3 action / 3 sound。改为全量写入 `constants.py` 中定义的所有枚举值，与 `ai-model-capability` spec 对齐。

### D8: 冷却只看异常种类，不看触发对象

冷却 key 从 `(view_id, exc_id, track_id)` 降为 `(view_id, exc_id)` 二元组。同一 View 中同一种异常触发后，在冷却时间内不再重复触发，无论是由哪个 track 引起的。

`_triggered` 和 `_ongoing` 的 key 类型同步变更。`_ft()` 方法仅在创建 SituationEvent 时用于记录触发对象的 track_id，不参与冷却判定。

**理由**: 与 D2 存在性告警一致 — 目前阶段关注"画面里有没有异常"，不关注"谁造成的"。简化冷却逻辑，后续可按需加回 per-track 精度。

## Risks / Trade-offs

- **[R1] AlertEngine 从异步改为同步被调** → 单帧处理时间略微增加。Mitigation: `feed()` 只做赋值，不做匹配；匹配仍在 `_check_loop`（5s 间隔）中异步执行。
- **[R2] 全局 ID 缓存多 View 污染** → 与现有 `_face_labels` 等全局 dict 有相同问题。Mitigation: `process_frame` 开头清空 `_active_action_type_ids`；`ActiveSignals` 在 pipeline 的 `_run_loop` 中提取，天然 per-frame per-view。
- **[R3] Sound 兼容路径只覆盖 SOUND_TYPE_MAP 15 类** → 新版 521 类危险检测不参与告警匹配。Mitigation: 当前 ExceptionDef 的 sound 条件只关联 YAMNetSoundType 枚举值，新版检测的 "Fighting"/"Riot" 等复合标签本就不在枚举表中。后续可扩展枚举表。

## Migration Plan

1. 新增 `ActiveSignals` 数据类和全局 ID 缓存
2. 修改 `VideoAIProcessor` 和 `YamnetRunner` 同步写入 ID 缓存
3. 修改 `AIPipeline._run_loop` 提取快照并传给 AlertEngine
4. 修改 `AlertEngine` 从快照读取，移除 EventBus 枚举信号订阅
5. 补齐 `seed.py` 和 debug 日志
6. 回归验证：确保 FLV 录制功能不受影响

无需数据迁移或配置变更。
