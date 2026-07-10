# Exception CRUD API (Delta)

## MODIFIED Requirements

### Requirement: Exception schema fields have descriptions

`exception_schema.py` 中的 ExceptionCreate 和 ExceptionResponse 各字段 SHALL 包含中文 Field description。精简版 API 不返回嵌套对象——group_id 为数字，前端 SHALL 按需独立查询关联信息。

#### Scenario: Swagger shows field descriptions for exception endpoints

- **WHEN** 前端开发者打开 `GET /api/v1/exceptions` 的 Swagger 文档
- **THEN** 每个字段（name, severity, group_id, face_result_id, fence_event_id, created_at）均有中文 description
- **AND** group_id 仅展示为数字（非嵌套对象）

#### Scenario: Frontend ExceptionResponse matches actual API response

- **WHEN** 前端调用 `GET /api/v1/exceptions`
- **THEN** 返回的 JSON 结构与前端 `ExceptionResponse` 类型一致
- **AND** 不包含 alert_group, entities, actions, sounds 嵌套字段
