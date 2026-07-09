## Why

异常/告警体系的数据库表（entity_types、action_types、sound_types、response_actions、alert_groups、exceptions 及 M2M 关联表）已建好，但表内无数据。AI 检测模型的能力（YOLO 15 类实体、SlowFast 15 类行为、YAMNet 15 类声音）是固定的，需要将这些枚举值 + 告警规则预置为种子数据，使系统启动后即可用。

## What Changes

- 新增种子数据 Python 脚本 `src/seed_data.py`，通过 SQLAlchemy ORM 插入数据，幂等可重复执行
- 插入 EntityType 15 条（YOLO 实体）、ActionType 15 条（SlowFast 行为）、SoundType 15 条（YAMNet 声音）
- 插入 ResponseAction 5 条（触发录制、发送通知、激活警报、调用 API、发送邮件）
- 插入 AlertGroup 4 条（INFO/WARNING/CRITICAL/EMERGENCY 分组）+ 绑定对应 ResponseAction
- 插入 ExceptionDef 8 条（入侵检测、暴力事件、武器检测、火灾检测、声音异常、非法攀爬、人员倒地、可疑徘徊）+ 绑定对应 EntityType/ActionType/SoundType
- 种子数据严格遵循 `constants.py` 中已定义的 IntEnum 值和 `异常类追加.md` 中的触发规则

## Capabilities

### New Capabilities

- `seed-data-script`: 预置 AI 检测枚举值与异常规则的种子数据脚本，幂等可重复执行，支持 `python -m src.seed_data` 运行

### Modified Capabilities

<!-- 无 — 纯数据填充，不修改任何模型/仓库/服务/API -->

## Impact

- **新增文件**: `src/seed_data.py` — 种子数据脚本
- **不修改**任何现有代码（模型/仓库/服务/API/配置）
