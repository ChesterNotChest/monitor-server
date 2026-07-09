## Context

异常/告警体系的数据库表已通过 SQLAlchemy ORM 定义完毕，API 和 Service 层也已完成 CRUD。所有表当前为空。需要将 AI 模型能力范围内的固定枚举值和参考异常规则预置入库。

数据来源：`异常类追加.md` 中定义的各模型能力枚举 + 异常检测触发规则示例。

## Goals / Non-Goals

**Goals:**
- 插入 15 条 EntityType（YOLO COCO 80 类中监控场景相关子集）
- 插入 15 条 ActionType（SlowFast Kinetics-400 中监控场景相关子集）
- 插入 15 条 SoundType（YAMNet AudioSet 中监控场景相关子集）
- 插入 5 条 ResponseAction（触发录制、通知、警报、API 回调、邮件）
- 插入 4 条 AlertGroup（INFO / WARNING / CRITICAL / EMERGENCY）及其 ResponseAction 绑定
- 插入 8 条 ExceptionDef 参考规则及其 AI 检测类型绑定
- 脚本幂等（重复执行不报错、不重复插入）

**Non-Goals:**
- 不通过 FastAPI 启动时自动执行（手动运行 `python -m src.seed_data`）
- 不实现 Alembic 数据库迁移
- 不修改任何现有模型/仓库/服务/API 代码

## Decisions

### 1. 实现方式：Python ORM 脚本（非 .sql 文件）

**选择**: 使用 SQLAlchemy ORM 编写种子脚本，而非纯 SQL INSERT 语句。

**理由**:
- 与现有代码风格一致（repo.create / 批量 insert）
- 可利用 `constants.py` 中已定义的 IntEnum，避免硬编码数值
- 跨数据库兼容（SQLite 和 MySQL 均可用）
- 幂等实现简单（查询后决定是否插入）

### 2. 幂等策略：逐条 UPSERT

**选择**: 执行前先 `SELECT` 检查是否存在同名记录，存在则跳过。

**理由**: SQLite 的 `INSERT OR IGNORE` 不支持 ORM 的关系字段；逐条检查虽略慢但种子数据量小（<100 条），可接受。若存在则 `UPDATE` 名称，保证数据一致。

### 3. 枚举值编号

**选择**: 严格使用 `constants.py` 中已定义的 IntEnum 值（1-based）。

DTO 中枚举从 0 开始编号是展示习惯；代码和数据库中使用 1-based 与现有枚举定义一致，无需映射。

### 4. AlertGroup 命名

**选择**: AlertGroup 名称使用中文，分 4 级：

| name | 绑定 ResponseAction |
|------|-------------------|
| 信息 | (无，仅记录) |
| 警告 | SEND_NOTIFICATION |
| 严重 | SEND_NOTIFICATION + TRIGGER_RECORDING |
| 紧急 | ACTIVATE_ALARM + SEND_NOTIFICATION + CALL_API + TRIGGER_RECORDING |

**理由**: 中文名与需求方沟通语言一致；绑定关系参照 `异常类追加.md` 触发规则表中的模式。

### 5. ExceptionDef 参考规则

**选择**: 创建 8 条参考异常规则，映射 `异常类追加.md` 中的示例：

| 异常名称 | severity | 绑定 entities | 绑定 actions | 绑定 sounds |
|---------|----------|-------------|-------------|------------|
| 入侵检测 | CRITICAL | PERSON | — | — |
| 暴力事件 | EMERGENCY | PERSON | FIGHTING, PUSHING, FALLING | — |
| 武器检测 | EMERGENCY | KNIFE, GUN | — | — |
| 火灾检测 | EMERGENCY | FIRE, SMOKE | — | — |
| 声音异常 | EMERGENCY | — | — | GUNSHOT, SCREAM, EXPLOSION |
| 非法攀爬 | WARNING | PERSON | CLIMBING | — |
| 人员倒地 | CRITICAL | PERSON | LYING_DOWN | — |
| 可疑徘徊 | WARNING | PERSON | LOITERING | — |

**理由**: 这些是需求文档明确列出的核心检测场景，作为初始种子数据可让系统启动后直接可用。

## Risks / Trade-offs

- **[R] 种子数据与业务演进不同步**: 后续新增 AI 检测类型时种子脚本不会自动感知 → 种子脚本是手动维护的参考起点，后续通过 API 管理界面增删
- **[R] AlertGroup 绑定粒度**: 当前绑定是固定的，所有 CRITICAL 级别使用相同的响应动作集合 → 这是合理的默认值，后续可通过 `PUT /alert-groups/{id}/responses` 调整
