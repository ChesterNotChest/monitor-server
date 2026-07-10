# Swagger Documentation Audit

## Purpose

确保 Swagger (`/docs`) 成为前端开发者唯一需要参考的 REST API 文档。对所有 Pydantic Schema 和 API 端点进行文档完整性审查与补全。

## ADDED Requirements

### Requirement: All Pydantic Field has description

所有被 FastAPI router 用作请求体或响应体的 Pydantic Field SHALL 包含 `description` 参数。description SHALL 使用中文，SHALL 足以让前端开发者理解字段含义而无需阅读后端源码。

#### Scenario: FenceCreate fields are documented

- **WHEN** 前端开发者打开 `POST /api/v1/fences` 的 Swagger 文档
- **THEN** `coords` 字段的 description 显示为 "4 点不规则四边形 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]（像素坐标系）"
- **AND** `dwell_time` 字段的 description 显示为 "停留时限（秒）"
- **AND** `density` 字段的 description 显示为 "密度阈值"

#### Scenario: Enum fields are self-documenting

- **WHEN** 前端开发者查看 `ExceptionCreate.severity` 字段
- **THEN** Swagger 展示该字段为枚举类型，description 说明各值的含义（如 "1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY"）

### Requirement: All endpoint has response_model

每个 REST 端点 SHALL 声明 `response_model`（或对无响应的端点使用 `status_code=204`）。返回 dict 的端点 SHALL 改为返回 Pydantic BaseModel，确保 Swagger 能推断并展示准确的响应结构。

#### Scenario: Logout endpoint returns typed response

- **WHEN** 前端开发者打开 `POST /api/v1/auth/logout`
- **THEN** Swagger 展示响应结构为 `{ ok: boolean }`
- **AND** 而非显示为未指定类型的 object

#### Scenario: Delete endpoint returns typed response

- **WHEN** 前端开发者打开 `DELETE /api/v1/views/{view_id}`
- **THEN** Swagger 展示响应结构为 `{ ok: boolean }`
- **AND** 而非显示为未指定类型的 object

#### Scenario: List endpoints return typed pagination

- **WHEN** 前端开发者打开 `GET /api/v1/views`
- **THEN** Swagger 展示响应结构为 `{ views: [ViewResponse] }`
- **AND** 而非显示为未指定类型的 object

### Requirement: Error responses are declared in Swagger

每个可能返回非 200 状态码的端点 SHALL 在 `@router.<method>(responses={...})` 中声明错误响应。声明 SHALL 包含状态码和中文 description。常见错误码包括 400 (参数校验失败)、401 (未认证)、403 (无权限)、404 (资源不存在)、409 (冲突)、422 (请求体校验失败)。

#### Scenario: Create endpoint declares conflict error

- **WHEN** 前端开发者打开 `POST /api/v1/persons`
- **THEN** Swagger 在 Responses 区域展示 `409: 名称已存在`

#### Scenario: Delete endpoint declares not found error

- **WHEN** 前端开发者打开 `DELETE /api/v1/fences/{fence_id}`
- **THEN** Swagger 在 Responses 区域展示 `404: 围栏不存在`

### Requirement: Endpoint docstring is Swagger-visible

每个端点函数的 docstring SHALL 包含端点的中文功能描述。受 RBAC 保护的端点 SHALL 在 docstring 中标注所需权限标识符。Swagger 会将 docstring 渲染为端点的 Markdown 描述。

#### Scenario: Protected endpoint shows permission

- **WHEN** 前端开发者打开 `PUT /api/v1/alerts/{alert_id}/handle`
- **THEN** Swagger 描述区域展示 "标记告警为已处理。\n\n**权限**: alert:handle"

#### Scenario: Public endpoint shows description

- **WHEN** 前端开发者打开 `GET /api/v1/views`
- **THEN** Swagger 描述区域展示 "列出所有监控视图"

### Requirement: Swagger Tags are consistent

所有 router 的 `tags` 参数 SHALL 使用统一的中文标签。同一业务领域的端点（如 events 和 events/stats）SHALL 使用相同的 Tag，确保 Swagger UI 中同一组的端点聚合展示。

#### Scenario: Events endpoints are grouped together

- **WHEN** 前端开发者打开 Swagger UI
- **THEN** `GET /api/v1/events`、`GET /api/v1/events/{id}`、`GET /api/v1/events/stats/by-exception`、`GET /api/v1/events/stats/trend` 全部聚合在 "事件日志" Tag 下
