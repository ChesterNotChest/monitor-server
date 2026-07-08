# Exception Model

**Purpose:** 定义异常枚举模型，组合 AI 检测结果（实体/行为/声音）构成异常规则，关联告警级别分组。

## Requirements

### Requirement: 异常枚举表定义
系统 SHALL 定义 `ExceptionDef` 模型，映射到 `exceptions` 表，存储异常类型及严重级别。

- `id`: 自增主键（Integer）
- `severity`: 严重级别（Enum `SeverityLevel`，非空），枚举值包括 `INFO`、`WARNING`、`CRITICAL`、`EMERGENCY`
- `group_id`: 外键关联 `alert_groups.id`（Integer，非空，索引）

#### Scenario: 创建异常类型
- **WHEN** 插入记录指定 `severity` 和 `group_id`
- **THEN** 系统持久化该异常类型

#### Scenario: 按严重级别查询异常
- **WHEN** 按 `severity` 过滤查询
- **THEN** 系统返回该严重级别下的所有异常类型

### Requirement: 异常-实体多对多关联
系统 SHALL 定义 `exception_entities` 关联表，建立异常与 YOLO 实体类型的多对多关系。

- `exception_id`: 外键关联 `exceptions.id`
- `entity_id`: 外键关联 `entity_types.id`

#### Scenario: 关联异常与实体类型
- **WHEN** 向 `exception_entities` 插入 `exception_id` 与 `entity_id`
- **THEN** 系统建立该异常与该实体类型的关联

### Requirement: 异常-行为多对多关联
系统 SHALL 定义 `exception_actions` 关联表，建立异常与 SlowFast 行为类型的多对多关系。

- `exception_id`: 外键关联 `exceptions.id`
- `action_id`: 外键关联 `action_types.id`

#### Scenario: 关联异常与行为类型
- **WHEN** 向 `exception_actions` 插入 `exception_id` 与 `action_id`
- **THEN** 系统建立该异常与该行为类型的关联

### Requirement: 异常-声音多对多关联
系统 SHALL 定义 `exception_sounds` 关联表，建立异常与 YAMNet 声音类型的多对多关系。

- `exception_id`: 外键关联 `exceptions.id`
- `sound_id`: 外键关联 `sound_types.id`

#### Scenario: 关联异常与声音类型
- **WHEN** 向 `exception_sounds` 插入 `exception_id` 与 `sound_id`
- **THEN** 系统建立该异常与该声音类型的关联
