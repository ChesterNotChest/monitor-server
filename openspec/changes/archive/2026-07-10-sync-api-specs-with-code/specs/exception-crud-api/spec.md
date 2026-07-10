## REMOVED Requirements

### Requirement: ExceptionDef 绑定 EntityType
**Reason**: 绑定/解绑路由（`/exceptions/{id}/entities`）未实现。计划在 Part C 中与告警引擎一起实施。
**Migration**: Part C 实施时从 git history 恢复此需求。

### Requirement: ExceptionDef 绑定 ActionType
**Reason**: 绑定/解绑路由（`/exceptions/{id}/actions`）未实现。计划在 Part C 中实施。
**Migration**: Part C 实施时从 git history 恢复此需求。

### Requirement: ExceptionDef 绑定 SoundType
**Reason**: 绑定/解绑路由（`/exceptions/{id}/sounds`）未实现。计划在 Part C 中实施。
**Migration**: Part C 实施时从 git history 恢复此需求。

## MODIFIED Requirements

### Requirement: ExceptionDef CRUD
系统 SHALL 提供 ExceptionDef（异常规则）的完整 CRUD API 与 Service。

#### Scenario: 创建异常规则
- **WHEN** 客户端 `POST /api/v1/exceptions` 请求体 `{"name": "测试", "severity": 3, "group_id": 1}`
- **THEN** 系统创建异常规则记录，返回 201

#### Scenario: 查询异常规则列表
- **WHEN** 客户端 `GET /api/v1/exceptions`
- **THEN** 系统返回所有异常规则列表

#### Scenario: 更新异常规则
- **WHEN** 客户端 `PUT /api/v1/exceptions/1` 请求体 `{"name": "测试", "severity": 4, "group_id": 2}`
- **THEN** 系统更新记录，返回更新后记录

#### Scenario: 删除异常规则
- **WHEN** 客户端 `DELETE /api/v1/exceptions/1`
- **THEN** 系统删除记录，返回 204
