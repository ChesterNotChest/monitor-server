# Exception CRUD API (Delta)

## ADDED Requirements

### Requirement: Exception endpoints declare complete response and error models

异常规则 CRUD 端点 SHALL 声明完整的 `response_model` 和可能的错误响应，确保 Swagger 展示 ExceptionResponse 的全部字段（含嵌套的 alert_group、entities、actions、sounds）。

#### Scenario: Exception list returns full structure

- **WHEN** 前端开发者打开 `GET /api/v1/exceptions`
- **THEN** Swagger 展示 ExceptionResponse 包含 id, name, severity, group_id, face_result_id, fence_event_id, created_at, alert_group, entities[], actions[], sounds[]
- **AND** 所有嵌套字段均有 description

#### Scenario: Create exception declares validation and conflict errors

- **WHEN** 前端开发者打开 `POST /api/v1/exceptions`
- **THEN** Swagger Responses 区域展示 `422: 请求体校验失败` 和 `404: 关联资源不存在`
- **AND** 描述区域展示 "**权限**: exception:manage"

#### Scenario: Delete exception declares not found error

- **WHEN** 前端开发者打开 `DELETE /api/v1/exceptions/{exc_id}`
- **THEN** Swagger Responses 区域展示 `404: 异常规则不存在`
