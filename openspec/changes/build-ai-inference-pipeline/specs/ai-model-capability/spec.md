# AI Model Capability

**Purpose:** 接入电子围栏事件类型，补全枚举事件体系。

## ADDED Requirements

### Requirement: FenceEventType 枚举模型

系统 SHALL 新增 `FenceEventType` 模型，映射到 `fence_event_types` 表。当前 SHALL 包含 `ENTERED (1)` 枚举值。

#### Scenario: 查询围栏事件类型

- **WHEN** 前端请求 `GET /api/v1/detection/fence-event-types`
- **THEN** 返回 `[{id: 1, name: "ENTERED"}]`

### Requirement: 枚举事件体系统一

系统 SHALL 将 EntityType、ActionType、SoundType、FaceRecognitionResult、FenceEventType 统一作为"枚举事件"体系成员。每个子功能产出对应类型的枚举事件列表，ExceptionDef 通过 M2M/FK 关联各类型事件。

#### Scenario: 所有枚举类型可被 ExceptionDef 引用

- **WHEN** 创建一条 ExceptionDef 规则
- **THEN** 可同时绑定 5 种枚举事件类型（entities、actions、sounds、face_result、fence_event）中的任意组合
