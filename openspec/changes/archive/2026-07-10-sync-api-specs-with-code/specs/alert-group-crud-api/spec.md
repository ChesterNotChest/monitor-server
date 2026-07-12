## REMOVED Requirements

### Requirement: ResponseAction CRUD
**Reason**: ResponseAction API 路由（`/response-actions`）未实现。ResponseAction 模型和 Repository 层存在，但 CRUD 端点计划在 Part C 中实施。
**Migration**: Part C 实施时从 git history 恢复此需求。

### Requirement: AlertGroup 绑定 ResponseAction
**Reason**: 告警分组与响应动作的绑定/解绑路由（`/alert-groups/{id}/responses`）未实现。计划在 Part C 中与 ResponseAction CRUD 一起实施。
**Migration**: Part C 实施时从 git history 恢复此需求。

## MODIFIED Requirements

### Requirement: AlertGroup CRUD
系统 SHALL 提供 AlertGroup（告警级别分组）的完整 CRUD API 与 Service。

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
