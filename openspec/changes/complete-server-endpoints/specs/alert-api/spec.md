# Alert API (Delta)

## ADDED Requirements

### Requirement: Alert endpoints declare response models and error responses

告警相关端点 SHALL 声明 `response_model` 和可能的错误响应，确保 Swagger 文档完整。

#### Scenario: Alert list declares paginated response

- **WHEN** 前端开发者打开 `GET /api/v1/alerts`
- **THEN** Swagger 展示 `AlertListResponse` 的完整结构（items, total, page, page_size）
- **AND** AlertResponse 中所有字段（id, view_id, exception_id, recording_id, timestamp）均有 description

#### Scenario: Handle endpoint declares not found error

- **WHEN** 前端开发者打开 `PUT /api/v1/alerts/{alert_id}/handle`
- **THEN** Swagger 的 Responses 区域展示 `404: 告警不存在`
- **AND** 描述区域展示 "**权限**: alert:handle"

#### Scenario: False alarm endpoint declares not found error

- **WHEN** 前端开发者打开 `PUT /api/v1/alerts/{alert_id}/false-alarm`
- **THEN** Swagger 的 Responses 区域展示 `404: 告警不存在`
- **AND** 描述区域展示 "**权限**: alert:handle"
