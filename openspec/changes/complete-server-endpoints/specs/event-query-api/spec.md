# Event Query API (Delta)

## ADDED Requirements

### Requirement: Events endpoints use unified Tag

events 路由（`/api/v1/events`）和 stats 路由（`/api/v1/events/stats`）SHALL 使用统一的 Swagger Tag。当前 events 使用 `["事件日志"]`，stats 使用 `["事件统计"]`——应统一为 `["事件日志"]`，使 4 个端点（列表、详情、按异常统计、趋势统计）在 Swagger UI 中聚合在同一分组下。

#### Scenario: All event endpoints grouped together

- **WHEN** 前端开发者打开 Swagger UI
- **THEN** `GET /events`、`GET /events/{id}`、`GET /events/stats/by-exception`、`GET /events/stats/trend` 全部在 "事件日志" 分组下

### Requirement: Event endpoints declare response models

事件相关端点 SHALL 声明清晰的 `response_model`，确保 Swagger 展示完整的响应结构。

#### Scenario: Stats by exception shows response structure

- **WHEN** 前端开发者打开 `GET /api/v1/events/stats/by-exception`
- **THEN** Swagger 展示响应为 `[{ exception_id, exception_severity, count }]`
- **AND** 每个字段均有 description

#### Scenario: Trend shows response structure

- **WHEN** 前端开发者打开 `GET /api/v1/events/stats/trend`
- **THEN** Swagger 展示响应为 `[{ period, count }]`
- **AND** granularity 查询参数在 Swagger 的 Parameters 区域展示，description 说明 "hour/day/month，默认 day"
