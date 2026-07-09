## ADDED Requirements

### Requirement: ExceptionDef CRUD
系统 SHALL 提供 ExceptionDef（异常规则）的完整 CRUD API 与 Service。

#### Scenario: 创建异常规则
- **WHEN** 客户端 `POST /api/v1/exceptions` 请求体 `{"severity": "CRITICAL", "group_id": 1}`
- **THEN** 系统创建异常规则记录，返回 201 和完整 JSON（含空 entities/actions/sounds 列表）

#### Scenario: 查询异常规则列表
- **WHEN** 客户端 `GET /api/v1/exceptions`
- **THEN** 系统返回所有异常规则列表，每个规则含已关联的 entities、actions、sounds 和 alert_group

#### Scenario: 按严重级别过滤
- **WHEN** 客户端 `GET /api/v1/exceptions?severity=CRITICAL`
- **THEN** 系统仅返回 severity 为 CRITICAL 的异常规则

#### Scenario: 查询单个异常规则详情
- **WHEN** 客户端 `GET /api/v1/exceptions/1`
- **THEN** 系统返回该规则完整信息，含所有关联数据

#### Scenario: 更新异常规则
- **WHEN** 客户端 `PUT /api/v1/exceptions/1` 请求体 `{"severity": "EMERGENCY", "group_id": 2}`
- **THEN** 系统更新 severity 和 group_id，返回更新后记录

#### Scenario: 删除异常规则
- **WHEN** 客户端 `DELETE /api/v1/exceptions/1`
- **THEN** 系统删除记录及所有 M2M 关联（CASCADE），返回 204

#### Scenario: 创建异常规则指定无效 group_id
- **WHEN** 客户端 `POST /api/v1/exceptions` 请求体 `{"severity": "CRITICAL", "group_id": 999}`
- **THEN** 系统返回 422 验证错误（外键约束违反）

### Requirement: ExceptionDef 绑定 EntityType
系统 SHALL 提供嵌套路由管理异常规则与实体检测类型的绑定关系。

#### Scenario: 绑定实体类型到异常规则
- **WHEN** 客户端 `POST /api/v1/exceptions/1/entities` 请求体 `{"entity_id": 2}`
- **THEN** 系统建立绑定，返回该规则当前的完整 entities 列表

#### Scenario: 解绑实体类型
- **WHEN** 客户端 `DELETE /api/v1/exceptions/1/entities/2`
- **THEN** 系统解除绑定，返回 204

#### Scenario: 绑定幂等
- **WHEN** 客户端重复绑定已存在的关联
- **THEN** 系统静默成功（幂等），不报错

### Requirement: ExceptionDef 绑定 ActionType
系统 SHALL 提供嵌套路由管理异常规则与行为检测类型的绑定关系。

#### Scenario: 绑定行为类型到异常规则
- **WHEN** 客户端 `POST /api/v1/exceptions/1/actions` 请求体 `{"action_id": 3}`
- **THEN** 系统建立绑定，返回该规则当前的完整 actions 列表

#### Scenario: 解绑行为类型
- **WHEN** 客户端 `DELETE /api/v1/exceptions/1/actions/3`
- **THEN** 系统解除绑定，返回 204

### Requirement: ExceptionDef 绑定 SoundType
系统 SHALL 提供嵌套路由管理异常规则与声音检测类型的绑定关系。

#### Scenario: 绑定声音类型到异常规则
- **WHEN** 客户端 `POST /api/v1/exceptions/1/sounds` 请求体 `{"sound_id": 1}`
- **THEN** 系统建立绑定，返回该规则当前的完整 sounds 列表

#### Scenario: 解绑声音类型
- **WHEN** 客户端 `DELETE /api/v1/exceptions/1/sounds/1`
- **THEN** 系统解除绑定，返回 204
