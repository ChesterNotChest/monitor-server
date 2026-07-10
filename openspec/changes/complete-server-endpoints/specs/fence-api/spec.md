# Fence API (Delta)

## ADDED Requirements

### Requirement: Fence schema fields have complete descriptions

FenceCreate 和 FenceResponse 的所有字段 SHALL 包含 description。coords 字段 SHALL 在 description 中说明其格式为 4 点不规则四边形像素坐标数组。

#### Scenario: Swagger shows coords format

- **WHEN** 前端开发者打开 `POST /api/v1/fences` 的 Swagger 文档
- **THEN** coords 字段的 description 说明格式为 `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`
- **AND** description 注明坐标系为像素坐标系
- **AND** description 注明数组长度限制为 4

#### Scenario: Swagger shows fence parameter descriptions

- **WHEN** 前端开发者查看 FenceCreate schema
- **THEN** dwell_time 的 description 说明 "停留时限（秒），默认 10"
- **AND** density 的 description 说明 "密度阈值，取值范围 0.0-1.0，默认 0.6"
- **AND** leave_frames 的 description 说明 "离开判定帧数，默认 5"

### Requirement: Fence endpoints declare error responses

电子围栏 CRUD 端点 SHALL 在 Swagger 中声明可能的错误响应。

#### Scenario: Create fence declares validation error

- **WHEN** 前端开发者打开 `POST /api/v1/fences`
- **THEN** Swagger Responses 区域展示 `422: 请求体校验失败`
- **AND** 描述区域展示 "**权限**: fence:manage"

#### Scenario: Delete fence declares not found error

- **WHEN** 前端开发者打开 `DELETE /api/v1/fences/{fence_id}`
- **THEN** Swagger Responses 区域展示 `404: 围栏不存在`
