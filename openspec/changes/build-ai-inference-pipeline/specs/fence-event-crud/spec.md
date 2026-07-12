# Fence Event CRUD

**Purpose:** FenceEventType 枚举值的完整 CRUD API，与 EntityType/ActionType/SoundType 路由风格一致。

## ADDED Requirements

### Requirement: FenceEventType CRUD

系统 SHALL 提供 FenceEventType（电子围栏事件类型）的完整 CRUD API。

#### Scenario: 创建围栏事件类型

- **WHEN** 客户端 `POST /api/v1/detection/fence-event-types` 请求体 `{"name": "ENTERED"}`
- **THEN** 系统创建记录，返回 201 和完整 JSON（id, name, created_at）

#### Scenario: 查询围栏事件类型列表

- **WHEN** 客户端 `GET /api/v1/detection/fence-event-types`
- **THEN** 系统返回所有围栏事件类型列表

#### Scenario: 更新围栏事件类型名称

- **WHEN** 客户端 `PUT /api/v1/detection/fence-event-types/{item_id}` 请求体 `{"name": "BREACHED"}`
- **THEN** 系统更新名称，返回更新后记录

#### Scenario: 删除围栏事件类型

- **WHEN** 客户端 `DELETE /api/v1/detection/fence-event-types/{item_id}`
- **THEN** 系统删除记录，返回 204

#### Scenario: 重复名称创建失败

- **WHEN** 客户端创建已存在的名称
- **THEN** 系统返回 409 Conflict

### Requirement: FenceEventType Service

系统 SHALL 在 `src/service/enum_task.py` 中新增 `FenceEventType` 对应的 Service 函数（`create_fence_event_type`、`list_fence_event_types`、`update_fence_event_type`、`delete_fence_event_type`），与已有的 `EntityType`、`ActionType`、`SoundType` CRUD 函数并列。

#### Scenario: Service 层创建

- **WHEN** `create_fence_event_type(db, "ENTERED")` 被调用
- **THEN** 写入 `fence_event_types` 表，返回 `FenceEventType` 实例
