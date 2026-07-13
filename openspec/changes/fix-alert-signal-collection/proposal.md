## Why

AlertEngine 通过 EventBus 独立采集 AI 枚举信号，但各模块发布到 EventBus 的 payload key 与 AlertEngine `_cids` 方法查找的 key 不一致，导致 ACTION/FACE/FENCE/SOUND 四种枚举信号全部丢失，告警匹配只能命中 ENTITY 条件。同时，绘制阶段已在 `_enrich_detection_labels()` 正确汇总了所有检测信息，AlertEngine 重复采集且数据不一致。此外，录制生命周期的冷却/时长/wind_down 逻辑已实现但缺少 debug 日志，无法运维验证。

## What Changes

- **Pipeline 每帧产出 `ActiveSignals` 快照**：从绘制阶段的汇总数据提取整数 ID 集合，同步喂给 AlertEngine，不再依赖 EventBus 采集枚举信号
- **扩展 VideoAIProcessor**：SlowFast 和 Face 模块在更新全局标签时同步记录整数 ID
- **新增 `_active_sound_type_ids` 全局存储**：YAMNet SOUND_TYPE_MAP 兼容路径发布时同步存储 sound_type_ids
- **AlertEngine 改为从快照读取**：`_check()` 直接用 Pipeline 传入的 `ActiveSignals`，去掉 EventBus 实体/动作/声音/人脸/围栏订阅
- **补齐 SEED 数据**：`seed_alerts()` 全量写入 `YOLOEntityType` / `SlowFastActionType` / `YAMNetSoundType` / `FaceRecognitionResult` / `FenceEventResult` 枚举值
- **增加 debug 日志**：冷却命中/跳过、wind_down 开始/结束、max_duration 触发、冷却重置，每个关键生命周期事件都有日志
- **FLV 录制能力保持不变**：RecordingSession 的 SRS 拉流 → FLV copy 逻辑不修改

## Capabilities

### New Capabilities
- `pipeline-active-signals`: Pipeline 每帧提取 AI 检测 integer ID 集合，作为 AlertEngine 的单一数据源

### Modified Capabilities
- `alert-api`: AlertEngine 数据采集从 EventBus 异步订阅改为 Pipeline 同步快照馈送；增加可选 debug 模式日志
- `ai-model-capability`: 各 AI 模块在产出枚举信号时，同步将 integer ID 写入模型级全局缓存
- `clip-replay`: 录制生命周期关键事件增加 debug 级别日志（冷却/时长/wind_down）

## Impact

- **修改文件**: `vision_pipeline.py`, `video_ai_processor.py`, `vision_annotation.py`, `audio_yamnet.py`, `alert_module/engine.py`, `seed.py`, `recorder.py`, `replay_task.py`
- **不修改**: `models/exception.py`, `schema/http/exception_schema.py`, `network/api/exception_router.py`（cooldown/max_recording/wind_down 字段和 API 已就绪）
- **不修改**: `replay_module/recorder.py` 的 SRS 拉流 → FLV copy 核心逻辑
- **风险**: 中。AlertEngine 数据采集链路变更，需确保冷却/录制生命周期行为不变
