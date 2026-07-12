# Alert Group CRUD API

**Purpose:** 定义 AlertGroup 告警分组的 CRUD API 与 Service。负责人和运维员可访问。

## Requirements

### Requirement: AlertGroup CRUD
系统 SHALL 提供 AlertGroup（告警级别分组）的完整 CRUD API 与 Service。

- `GET /api/v1/alert-groups` — 列表
- `POST /api/v1/alert-groups` — 创建告警分组
- `PUT /api/v1/alert-groups/{id}` — 更新告警分组
- `DELETE /api/v1/alert-groups/{id}` — 删除告警分组

#### Scenario: 创建告警分组
- **WHEN** 客户端 `POST /api/v1/alert-groups` 请求体 `{"name": "高优先级"}`
- **THEN** 系统创建告警分组记录，返回 201

#### Scenario: 查询告警分组列表
- **WHEN** 客户端 `GET /api/v1/alert-groups`
- **THEN** 系统返回所有告警分组列表

#### Scenario: 更新告警分组名称
- **WHEN** 客户端 `PUT /api/v1/alert-groups/1` 请求体 `{"name": "紧急优先级"}`
- **THEN** 系统更新名称，返回更新后记录

#### Scenario: 删除告警分组
- **WHEN** 客户端 `DELETE /api/v1/alert-groups/1`
- **THEN** 系统删除记录，返回 204
