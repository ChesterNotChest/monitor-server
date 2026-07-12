## MODIFIED Requirements

### Requirement: EntityType CRUD
系统 SHALL 提供 EntityType（YOLO 目标检测实体类型）的 CRUD API 与 Service。路由前缀为 `/api/v1/detection/entity-types`。

#### Scenario: 创建实体类型
- **WHEN** 客户端 `POST /api/v1/detection/entity-types` 请求体 `{"name": "person"}`
- **THEN** 系统创建实体类型记录，返回 201

#### Scenario: 查询实体类型列表
- **WHEN** 客户端 `GET /api/v1/detection/entity-types`
- **THEN** 系统返回所有实体类型列表

#### Scenario: 更新实体类型名称
- **WHEN** 客户端 `PUT /api/v1/detection/entity-types/1` 请求体 `{"name": "human"}`
- **THEN** 系统更新名称，返回更新后记录

#### Scenario: 删除实体类型
- **WHEN** 客户端 `DELETE /api/v1/detection/entity-types/1`
- **THEN** 系统删除记录，返回 204

### Requirement: ActionType CRUD
系统 SHALL 提供 ActionType（SlowFast 行为识别类型）的 CRUD API。路由前缀为 `/api/v1/detection/action-types`。

#### Scenario: 创建行为类型
- **WHEN** 客户端 `POST /api/v1/detection/action-types` 请求体 `{"name": "walking"}`
- **THEN** 系统创建行为类型记录，返回 201

#### Scenario: 查询行为类型列表
- **WHEN** 客户端 `GET /api/v1/detection/action-types`
- **THEN** 系统返回所有行为类型列表

#### Scenario: 删除行为类型
- **WHEN** 客户端 `DELETE /api/v1/detection/action-types/1`
- **THEN** 系统删除记录，返回 204

### Requirement: SoundType CRUD
系统 SHALL 提供 SoundType（YAMNet 音频分类类型）的 CRUD API。路由前缀为 `/api/v1/detection/sound-types`。

#### Scenario: 创建声音类型
- **WHEN** 客户端 `POST /api/v1/detection/sound-types` 请求体 `{"name": "gunshot"}`
- **THEN** 系统创建声音类型记录，返回 201

#### Scenario: 查询声音类型列表
- **WHEN** 客户端 `GET /api/v1/detection/sound-types`
- **THEN** 系统返回所有声音类型列表

#### Scenario: 删除声音类型
- **WHEN** 客户端 `DELETE /api/v1/detection/sound-types/1`
- **THEN** 系统删除记录，返回 204
