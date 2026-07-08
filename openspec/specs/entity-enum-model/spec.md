# Entity Enum Model

**Purpose:** 定义 YOLO 目标检测实体类别枚举模型，用于标注检测到的对象类型。

## Requirements

### Requirement: 实体类型枚举表定义
系统 SHALL 定义 `EntityType` 模型，映射到 `entity_types` 表，存储 YOLO 目标检测的实体类别枚举。

- `id`: 自增主键（Integer）
- `name`: 实体类别名称（String，唯一，非空），如 `person`、`car`、`dog` 等

#### Scenario: 注册 YOLO 实体类别
- **WHEN** 向 `entity_types` 表插入实体名称
- **THEN** 系统持久化该实体类型枚举值

#### Scenario: 查询所有实体类型
- **WHEN** 查询 `entity_types` 全表
- **THEN** 系统返回所有已注册的实体类别列表
