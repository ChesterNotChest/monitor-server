# Exception Model

**Purpose:** 异常定义模型的变更——新增电子围栏事件的 FK 关联。

## MODIFIED Requirements

### Requirement: ExceptionDef 支持围栏事件

系统 SHALL 在 `ExceptionDef` 模型上新增 `fence_event_id` FK 字段，关联 `fence_event_types.id`（Integer，可空，索引）。一条 ExceptionDef SHALL 可同时绑定 EntityType、ActionType、SoundType、FaceRecognitionResult 和 FenceEventType。

#### Scenario: 创建围栏异常规则

- **WHEN** 创建 ExceptionDef 绑定 `fence_event_id=1 (ENTERED)` + `entity_type_id=1 (PERSON)`
- **THEN** 同时检测到人形 + 围栏闯入时触发该异常规则

#### Scenario: 不绑定围栏事件的规则

- **WHEN** 创建 ExceptionDef 仅绑定 EntityType 和 ActionType，不绑定 fence_event
- **THEN** `fence_event_id` 为 NULL，规则不检测围栏条件
