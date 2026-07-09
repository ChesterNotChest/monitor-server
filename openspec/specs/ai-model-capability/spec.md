# AI Model Capability

**Purpose:** 定义智能分析模块使用的模型、能力边界、与枚举表的映射关系。

## Requirements

### Requirement: YOLO11 目标检测模型

系统 SHALL 使用 YOLO11n（COCO 预训练）作为默认目标检测模型，权重文件存放于 `src/third-party/yolo/yolo11n.pt`（5.4 MB）。

YOLO11 COCO 80 类中 SHALL 映射到 `EntityType` 枚举的类别为：

| EntityType 枚举 | COCO 类 |
|-----------------|---------|
| PERSON (1) | person (0) |
| CAR (2) | car (2) |
| TRUCK (3) | truck (7) |
| BUS (4) | bus (5) |
| MOTORCYCLE (5) | motorcycle (3) |
| BICYCLE (6) | bicycle (1) |
| DOG (7) | dog (16) |
| CAT (8) | cat (15) |
| BIRD (9) | bird (14) |
| BACKPACK (10) | backpack (24) |
| SUITCASE (11) | suitcase (28) |
| KNIFE (12) | knife (43) |

未覆盖的枚举值 GUN (13)、FIRE (14)、SMOKE (15) SHALL 通过后续微调补齐。

#### Scenario: 检测行人

- **WHEN** 视频帧中出现行人
- **THEN** 系统输出 `EntityType.PERSON`，可用于电子围栏、人数统计

#### Scenario: 检测已知物件

- **WHEN** 画面中出现刀具（knife）
- **THEN** 系统输出 `EntityType.KNIFE`，触发异常物品告警

### Requirement: SlowFast Kinetics-400 场景级行为分类

系统 SHALL 使用 SlowFast R-50（Kinetics-400 预训练）作为场景级行为分类模型，权重文件存放于 `src/third-party/slowfast/SLOWFAST_8x8_R50.pkl`（139 MB）。

Kinetics-400 中 SHALL 映射到 `SlowFastActionType` 枚举的类别为：

| ActionType 枚举 | Kinetics-400 类 |
|-----------------|-----------------|
| WALKING (1) | walking |
| RUNNING (2) | running |
| FALLING (3) | falling down |
| FIGHTING (4) | fighting |
| CLIMBING (7) | climbing |
| THROWING (8) | throwing |
| POINTING (9) | pointing |
| WAVING (10) | waving hand |
| HUGGING (11) | hugging |
| PUSHING (12) | pushing |
| SITTING (14) | sitting |
| STANDING (15) | standing |

LOITERING (5)、CROWDING (6)、LYING_DOWN (13) SHALL 通过时序逻辑推导（如站立超过 N 秒→徘徊，多人近距离→聚集），而非依赖模型直接输出。

#### Scenario: 检测跌倒

- **WHEN** 人员从站立姿态快速变为倒地且停留超过阈值
- **THEN** 系统输出 `ActionType.FALLING`，触发异常行为告警

#### Scenario: 检测奔跑

- **WHEN** 画面中人物持续高速移动
- **THEN** 系统输出 `ActionType.RUNNING`

### Requirement: SlowFast AVA 人物级动作检测

系统 SHALL 使用 SlowFast R-50（AVA 2.2 微调）作为人物级动作检测模型，权重文件存放于 `src/third-party/slowfast/SLOWFAST_8x8_R50_DETECTION.pyth`（258 MB）。

AVA 2.2 包含 60 个细粒度动作类，直接覆盖原始需求"抽烟"场景的 smoking 类。其他可用类包括：drink、eat、listen to music、talk on phone、read、cut、stir 等。

#### Scenario: 检测抽烟行为

- **WHEN** 画面中人物手持香烟靠近嘴部
- **THEN** 系统输出 smoking 检测框，触发抽烟告警

#### Scenario: Kinetics 与 AVA 并行推理

- **WHEN** 一帧画面同时需要场景级分类和人物级检测
- **THEN** 两个模型独立推理，Kinetics 输出全局行为标签，AVA 输出人物级检测框，结果合并后统一处理

### Requirement: YAMNet 音频分类

系统 SHALL 使用 YAMNet（tensorflow-hub，AudioSet 521 类预训练）作为音频分类模型。权重由 tensorflow-hub API 管理，首次调用时自动缓存。

AudioSet 521 类 SHALL 映射到 `YAMNetSoundType` 枚举的全部 15 个类别：

| SoundType 枚举 | AudioSet 类 |
|----------------|-------------|
| GUNSHOT (1) | Gunshot, gunfire |
| SCREAM (2) | Scream |
| SIREN (3) | Siren |
| EXPLOSION (4) | Explosion |
| GLASS_BREAKING (5) | Shatter, glass breaking |
| DOG_BARKING (6) | Bark |
| CAR_HORN (7) | Vehicle horn |
| ENGINE (8) | Engine |
| BABY_CRYING (9) | Baby cry, infant cry |
| ALARM (10) | Alarm |
| THUNDER (11) | Thunder |
| WIND (12) | Wind |
| RAIN (13) | Rain |
| FOOTSTEPS (14) | Footsteps |
| SILENCE (15) | Silence |

YAMNet 覆盖率为 15/15（100%）。

#### Scenario: 检测尖叫声

- **WHEN** 音频流中检测到 Scream 类别
- **THEN** 系统输出 `SoundType.SCREAM`，结合视频检测结果综合判断异常

### Requirement: face_recognition 人脸识别

系统 SHALL 使用 face_recognition（dlib wrapper，HOG + CNN）作为人脸检测与特征提取模型。模型文件随 pip 包安装，无需独立管理。

128D 人脸特征向量 SHALL 与 `NamedPerson` 表关联，用于"未录入人员识别"场景。

#### Scenario: 检测未录入人员

- **WHEN** 画面中出现人脸，128D 特征向量与 NamedPerson 库均不匹配
- **THEN** 系统标记该面部为"未录入人员"，产生告警
