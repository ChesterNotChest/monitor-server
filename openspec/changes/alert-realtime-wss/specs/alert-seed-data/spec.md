# Alert Seed Data

## Purpose

系统初始化时预置告警规则种子数据，确保 AlertEngine 有可匹配的 ExceptionDef 规则。

## ADDED Requirements

### Requirement: Seed data includes entity types

系统 SHALL 在 `seed.py` 中预置基础实体类型（person、car、dog、cat 等），
对应 YOLO COCO 数据集的常见类别。

#### Scenario: Entity types seeded

- **WHEN** 系统首次启动且 DB 为空
- **THEN** `entity_types` 表包含预设的实体类型记录

### Requirement: Seed data includes alert group

系统 SHALL 预置至少一个告警分组（如 "默认告警组"），关联最低严重级别。

#### Scenario: Alert group seeded

- **WHEN** 系统首次启动且 DB 为空
- **THEN** `alert_groups` 表包含"默认告警组"

### Requirement: Seed data includes exception definition

系统 SHALL 预置至少一条异常定义规则（如 "人员出现"），关联实体类型和告警分组，
使 AlertEngine 在 YOLO 检测到 person 时能触发告警。

#### Scenario: Exception definition seeded

- **WHEN** 系统首次启动且 DB 为空
- **THEN** `exception_defs` 表包含预设的异常规则
- **AND** AlertEngine 能在 YOLO 检测到匹配实体时创建 SituationEvent
