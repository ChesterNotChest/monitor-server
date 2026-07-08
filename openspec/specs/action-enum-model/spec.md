# Action Enum Model

**Purpose:** 定义 SlowFast 行为识别类别枚举模型，用于标注检测到的人物行为类型。

## Requirements

### Requirement: 人物行为枚举表定义
系统 SHALL 定义 `ActionType` 模型，映射到 `action_types` 表，存储 SlowFast 行为识别的行为类别枚举。

- `id`: 自增主键（Integer）
- `name`: 行为类别名称（String，唯一，非空），如 `walking`、`running`、`falling` 等

#### Scenario: 注册 SlowFast 行为类别
- **WHEN** 向 `action_types` 表插入行为名称
- **THEN** 系统持久化该行为类型枚举值

#### Scenario: 查询所有行为类型
- **WHEN** 查询 `action_types` 全表
- **THEN** 系统返回所有已注册的行为类别列表
