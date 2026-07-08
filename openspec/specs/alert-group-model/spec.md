# Alert Group Model

**Purpose:** 定义告警级别分组数据模型，用于对异常进行优先级分层。

## Requirements

### Requirement: 告警级别分组表定义
系统 SHALL 定义 `AlertGroup` 模型，映射到 `alert_groups` 表，存储告警优先级分组。

- `id`: 自增主键（Integer）
- `name`: 分组名称（String，唯一，非空），如 `低优先级`、`中优先级`、`高优先级`

#### Scenario: 创建告警分组
- **WHEN** 插入记录提供分组名称
- **THEN** 系统持久化该告警分组

#### Scenario: 查询所有告警分组
- **WHEN** 查询 `alert_groups` 全表
- **THEN** 系统返回所有告警级别分组
