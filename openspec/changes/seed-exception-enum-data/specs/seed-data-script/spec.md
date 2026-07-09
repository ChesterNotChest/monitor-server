## ADDED Requirements

### Requirement: 枚举表种子数据
系统 SHALL 提供种子数据脚本，预置 AI 检测模型能力范围内的枚举值到对应数据库表。

#### Scenario: 插入 EntityType 种子数据
- **WHEN** 执行 `python -m src.seed_data`
- **THEN** entity_types 表包含 15 条 YOLO 实体类型记录（PERSON / CAR / TRUCK / BUS / MOTORCYCLE / BICYCLE / DOG / CAT / BIRD / BACKPACK / SUITCASE / KNIFE / GUN / FIRE / SMOKE）

#### Scenario: 插入 ActionType 种子数据
- **WHEN** 执行种子脚本
- **THEN** action_types 表包含 15 条 SlowFast 行为类型记录（WALKING / RUNNING / FALLING / FIGHTING / LOITERING / CROWDING / CLIMBING / THROWING / POINTING / WAVING / HUGGING / PUSHING / LYING_DOWN / SITTING / STANDING）

#### Scenario: 插入 SoundType 种子数据
- **WHEN** 执行种子脚本
- **THEN** sound_types 表包含 15 条 YAMNet 声音类型记录（GUNSHOT / SCREAM / SIREN / EXPLOSION / GLASS_BREAKING / DOG_BARKING / CAR_HORN / ENGINE / BABY_CRYING / ALARM / THUNDER / WIND / RAIN / FOOTSTEPS / SILENCE）

### Requirement: 响应动作与告警分组种子数据
系统 SHALL 预置 ResponseAction 和 AlertGroup 及其绑定关系。

#### Scenario: 插入 ResponseAction
- **WHEN** 执行种子脚本
- **THEN** response_actions 表包含 5 条记录（触发录制 / 发送通知 / 激活警报 / 调用 API / 发送邮件）

#### Scenario: 插入 AlertGroup 并绑定 ResponseAction
- **WHEN** 执行种子脚本
- **THEN** alert_groups 表包含 4 条记录（信息 / 警告 / 严重 / 紧急），各分组已绑定对应响应动作

### Requirement: 异常规则种子数据
系统 SHALL 预置 8 条参考异常规则及其 AI 检测类型绑定。

#### Scenario: 插入 ExceptionDef 参考规则
- **WHEN** 执行种子脚本
- **THEN** exceptions 表包含 8 条记录（入侵检测 / 暴力事件 / 武器检测 / 火灾检测 / 声音异常 / 非法攀爬 / 人员倒地 / 可疑徘徊），每条均已绑定对应 EntityType/ActionType/SoundType

### Requirement: 幂等执行
种子脚本 SHALL 支持重复执行而不产生错误或重复数据。

#### Scenario: 重复执行种子脚本
- **WHEN** 种子脚本已执行过，再次运行
- **THEN** 所有枚举记录保持不变，不产生重复条目，不报错
