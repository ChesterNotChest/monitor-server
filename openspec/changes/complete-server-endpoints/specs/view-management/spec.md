# View Management (Delta)

## ADDED Requirements

### Requirement: View response types are fully declared

所有 View 相关端点 SHALL 使用显式的 Pydantic 响应模型（非裸 dict），确保 Swagger 展示完整的响应结构。

#### Scenario: Delete view returns typed response

- **WHEN** 前端开发者打开 `DELETE /api/v1/views/{view_id}`
- **THEN** Swagger 展示响应结构为 `{ ok: boolean }`，由 DeleteResponse 模型定义
- **AND** 而非显示为未指定类型的 object

#### Scenario: List views returns typed wrapper

- **WHEN** 前端开发者打开 `GET /api/v1/views`
- **THEN** Swagger 展示响应结构为 `{ views: [ViewResponse] }`，由 ViewListResponse 模型定义
- **AND** 而非显示为未指定类型的 object

#### Scenario: View create error is documented

- **WHEN** 前端开发者打开 `POST /api/v1/views`
- **THEN** Swagger Responses 区域展示 `404: 设备不存在`
- **AND** Swagger 展示 `audio_id` 和 `video_id` 为 JSON body 字段（非 query 参数）
