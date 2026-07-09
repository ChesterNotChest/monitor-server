# Alert Group CRUD API

**Purpose:** 定义 AlertGroup 告警分组的 CRUD API 与 Service，含独立 ResponseAction 枚举管理路由 + 嵌套绑定/解绑路由。

## Requirements

### Requirement: ResponseAction CRUD
系统 SHALL 提供 ResponseAction（响应动作枚举）的独立 CRUD API 与 Service。

#### Scenario: 创建响应动作
- **WHEN** 客户端 `POST /api/v1/response-actions` 请求体 `{"name": "trigger_recording"}`
- **THEN** 系统创建响应动作记录，返回 201 和完整 JSON

#### Scenario: 查询响应动作列表
- **WHEN** 客户端 `GET /api/v1/response-actions`
- **THEN** 系统返回所有响应动作列表

#### Scenario: 更新响应动作名称
- **WHEN** 客户端 `PUT /api/v1/response-actions/1` 请求体 `{"name": "send_sms"}`
- **THEN** 系统更新名称，返回更新后记录

#### Scenario: 删除响应动作
- **WHEN** 客户端 `DELETE /api/v1/response-actions/1`
- **THEN** 系统删除记录，返回 204

### Requirement: AlertGroup CRUD
系统 SHALL 提供 AlertGroup（告警级别分组）的完整 CRUD API 与 Service。

#### Scenario: 创建告警分组
- **WHEN** 客户端 `POST /api/v1/alert-groups` 请求体 `{"name": "高优先级"}`
- **THEN** 系统创建告警分组记录，返回 201

#### Scenario: 查询告警分组列表
- **WHEN** 客户端 `GET /api/v1/alert-groups`
- **THEN** 系统返回所有告警分组列表，每个分组含已绑定的 `responses` 列表

#### Scenario: 查询单个告警分组详情
- **WHEN** 客户端 `GET /api/v1/alert-groups/1`
- **THEN** 系统返回该分组完整信息，含已绑定的响应动作列表

#### Scenario: 更新告警分组名称
- **WHEN** 客户端 `PUT /api/v1/alert-groups/1` 请求体 `{"name": "紧急优先级"}`
- **THEN** 系统更新名称，返回更新后记录

#### Scenario: 删除告警分组
- **WHEN** 客户端 `DELETE /api/v1/alert-groups/1`
- **THEN** 系统删除记录及关联的绑定关系（CASCADE），返回 204

### Requirement: AlertGroup 绑定 ResponseAction
系统 SHALL 提供嵌套路由管理告警分组与响应动作的绑定关系。

#### Scenario: 绑定响应动作到告警分组
- **WHEN** 客户端 `POST /api/v1/alert-groups/1/responses` 请求体 `{"response_id": 3}`
- **THEN** 系统建立绑定关系，返回该分组当前的完整 responses 列表

#### Scenario: 重复绑定幂等
- **WHEN** 客户端再次 `POST /api/v1/alert-groups/1/responses` 请求体 `{"response_id": 3}`
- **THEN** 系统静默成功（幂等），不报错

#### Scenario: 解绑响应动作
- **WHEN** 客户端 `DELETE /api/v1/alert-groups/1/responses/3`
- **THEN** 系统解除绑定关系，返回 204

#### Scenario: 解绑不存在的绑定幂等
- **WHEN** 客户端 `DELETE /api/v1/alert-groups/1/responses/99`（不存在的绑定）
- **THEN** 系统静默成功（幂等），不报错

#### Scenario: 绑定到不存在的分组
- **WHEN** 客户端 `POST /api/v1/alert-groups/999/responses`
- **THEN** 系统返回 404 Not Found
