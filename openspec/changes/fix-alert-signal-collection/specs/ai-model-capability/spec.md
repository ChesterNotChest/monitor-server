# AI Model Capability (delta)

## ADDED Requirements

### Requirement: 模块级整数 ID 输出
各 AI 检测模块在产出检测结果时 SHALL 同步将整数枚举 ID 写入模块级全局缓存，供 Pipeline 提取 `ActiveSignals`。

- YOLO Detector SHALL 继续在 `Detection.entity_type_id` 中设置 `YOLOEntityType` 整数值（已有）
- SlowFast Runner SHALL 在 `collect_results` 返回时，同步更新 `_active_action_type_ids` 为识别到的 `SlowFastActionType` 整数集合
- Face Recognizer SHALL 在 `get_face_labels` 之外提供结果查询能力，Pipeline 检测到 Stranger 时设 `face_result_ids = {2}`
- YAMNet Runner SHALL 在 SOUND_TYPE_MAP 兼容路径发布时，同步更新 `_active_sound_type_ids` 为匹配的 `YAMNetSoundType` 整数集合

#### Scenario: SlowFast 识别打架
- **WHEN** SlowFast 输出 `action_type_id=4`（FIGHTING）
- **THEN** `_active_action_type_ids` 包含 `4`

#### Scenario: YAMNet 检测枪声
- **WHEN** YAMNet SOUND_TYPE_MAP 路径检测到 class_id=421 对应 GUNSHOT (sound_type_val=0)
- **THEN** `_active_sound_type_ids` 包含 `1`（YAMNetSoundType.GUNSHOT = 1）

## MODIFIED Requirements

### Requirement: SEED 枚举数据全量对齐
系统 SHALL 在启动 seed 中幂等补齐 `constants.py` 定义的枚举值到数据库枚举表：

- `EntityType`: 全部 12 个 `YOLOEntityType` 值
- `ActionType`: 全部 16 个 `SlowFastActionType` 值
- `SoundType`: 全部 15 个 `YAMNetSoundType` 值
- `face_recognition_results`: 3 个 `FaceRecognitionResult` 值
- `fence_event_types`: 2 个 `FenceEventResult` 值，由 `seed_fence_events()` 保证 `ENTERED` / `TOO_CLOSE` 就绪

补齐 SHALL 以 `constants.py` 的固定整数枚举为准，最终数据库 ID/name SHALL 与 AI 管线产出的整数信号一致。对于历史存量库，系统 SHOULD 先迁移错位枚举，再补齐缺失项，避免告警规则匹配到错误类型。

#### Scenario: 首次启动覆盖全部枚举
- **WHEN** 系统首次启动且枚举表为空
- **THEN** EntityType 有 12 行，ActionType 有 16 行，SoundType 有 15 行，face_recognition_results 有 3 行，fence_event_types 有 2 行

#### Scenario: 存量库只包含部分旧枚举
- **WHEN** `entity_types`、`action_types`、`sound_types` 已有部分记录且 `face_recognition_results` 为空
- **THEN** seed SHALL 只插入缺失枚举，使 EntityType 达到 12 行、ActionType 达到 16 行、SoundType 达到 15 行、face_recognition_results 达到 3 行
- **AND** 最终 ID/name 与 `constants.py` 对齐，已有业务规则在迁移后仍引用相同语义的枚举
