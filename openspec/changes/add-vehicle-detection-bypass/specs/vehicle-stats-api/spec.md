# Vehicle Stats API

车辆统计 REST API — 查询指定 View 的累计和当前帧车辆统计数据。

## ADDED Requirements

### Requirement: 查询 View 车辆统计

系统 SHALL 暴露 `GET /api/v1/views/{view_id}/vehicle-stats/` 端点。当 View 存在且 AI 管线处于活跃状态时，返回累计和当前帧的车辆统计数据。不需要特殊 RBAC 权限（公开可读，与仪表盘同级）。

#### Scenario: 活跃 View 返回统计数据

- **WHEN** 客户端请求 `GET /api/v1/views/1/vehicle-stats/` 且 View 1 的管线正在运行
- **THEN** 返回 200，响应体包含 `total_unique`、`current_frame`、`fps`
- **AND** `total_unique` 包含 5 个车辆类别的累计去重计数
- **AND** `current_frame` 包含当前帧的去重车辆数

#### Scenario: View 存在但管线未启动

- **WHEN** 客户端请求 `GET /api/v1/views/1/vehicle-stats/` 且 View 1 存在但 AI 管线未启动
- **THEN** 返回 200，`total_unique` 所有值为 0，`current_frame` 所有值为 0

#### Scenario: View 不存在

- **WHEN** 客户端请求 `GET /api/v1/views/999/vehicle-stats/`
- **THEN** 返回 404，错误信息包含 "View not found"

#### Scenario: 未认证访问

- **WHEN** 客户端未携带有效 JWT Token 请求该端点
- **THEN** 返回 401

### Requirement: 响应数据格式

响应体 SHALL 符合以下 JSON Schema：

```json
{
  "view_id": 1,
  "total_unique": {"car": 15, "truck": 3, "bus": 2, "motorcycle": 8, "bicycle": 5},
  "current_frame": {"car": 2, "truck": 0, "bus": 1, "motorcycle": 1, "bicycle": 0},
  "fps": 15.2
}
```

所有计数字段 SHALL 为非负整数。`total_unique` 的键 SHALL 使用英文名 `car`、`truck`、`bus`、`motorcycle`、`bicycle`。

#### Scenario: 响应包含所有 5 个类别

- **WHEN** 返回统计数据
- **THEN** `total_unique` 包含 5 个键：`car`、`truck`、`bus`、`motorcycle`、`bicycle`
- **AND** 即使某类别计数为 0，仍返回该键

#### Scenario: fps 字段

- **WHEN** 返回统计数据
- **THEN** `fps` 字段反映 AI 管线的当前实际帧率（浮点数）
