## ADDED Requirements

### Requirement: 创建命名人物
系统 SHALL 提供 API 创建命名人物，接受姓名和可选的头像图片，返回创建的人物信息（含 ID、name、avatar_path、feat_json_id、created_at）。

#### Scenario: 仅传入姓名创建人物
- **WHEN** 客户端 `POST /api/v1/persons` 请求体 `{"name": "张三"}`
- **THEN** 系统创建人物记录，`avatar_path` 和 `feat_json_id` 为 null，返回 201 状态码和完整人物 JSON

#### Scenario: 同时上传头像创建人物
- **WHEN** 客户端 `POST /api/v1/persons` 以 multipart/form-data 发送 `name=李四` 和 `avatar=@face.jpg`
- **THEN** 系统保存头像图片到本地存储，创建人物记录且 `avatar_path` 为相对路径，返回 201

#### Scenario: 姓名为空创建失败
- **WHEN** 客户端 `POST /api/v1/persons` 请求体 `{"name": ""}`
- **THEN** 系统返回 422 验证错误

#### Scenario: 重复姓名创建失败
- **WHEN** 客户端尝试创建已存在的姓名
- **THEN** 系统返回 409 Conflict 错误

### Requirement: 查询命名人物列表
系统 SHALL 提供分页查询所有命名人物的 API。

#### Scenario: 默认分页查询
- **WHEN** 客户端 `GET /api/v1/persons`
- **THEN** 系统返回第一页（默认 20 条）人物列表及总数

#### Scenario: 指定分页参数查询
- **WHEN** 客户端 `GET /api/v1/persons?page=2&page_size=10`
- **THEN** 系统返回第 2 页 10 条记录及总数

### Requirement: 查询单个命名人物
系统 SHALL 提供按 ID 查询单个人物详情的 API。

#### Scenario: 查询存在的人物
- **WHEN** 客户端 `GET /api/v1/persons/1`
- **THEN** 系统返回该人物完整信息（id、name、avatar_path、feat_json_id、created_at）

#### Scenario: 查询不存在的人物
- **WHEN** 客户端 `GET /api/v1/persons/99999`
- **THEN** 系统返回 404 Not Found

### Requirement: 更新命名人物信息
系统 SHALL 提供按 ID 更新人物姓名或头像路径的 API。

#### Scenario: 更新姓名
- **WHEN** 客户端 `PUT /api/v1/persons/1` 请求体 `{"name": "王五"}`
- **THEN** 系统更新该人物姓名为"王五"，返回更新后的完整记录

#### Scenario: 更新不存在的人物
- **WHEN** 客户端 `PUT /api/v1/persons/99999` 请求体 `{"name": "王五"}`
- **THEN** 系统返回 404 Not Found

#### Scenario: 更新为已存在的姓名
- **WHEN** 客户端尝试将姓名更新为另一人物已使用的姓名
- **THEN** 系统返回 409 Conflict 错误

### Requirement: 删除命名人物
系统 SHALL 提供按 ID 删除命名人物及其关联的头像文件（如有）的 API。

#### Scenario: 删除存在的人物（含头像文件）
- **WHEN** 客户端 `DELETE /api/v1/persons/1` 且该人物有头像文件
- **THEN** 系统删除数据库记录及其头像文件，返回 204 No Content

#### Scenario: 删除存在的人物（无头像文件）
- **WHEN** 客户端 `DELETE /api/v1/persons/2` 且该人物无头像文件
- **THEN** 系统仅删除数据库记录，返回 204 No Content

#### Scenario: 删除不存在的人物
- **WHEN** 客户端 `DELETE /api/v1/persons/99999`
- **THEN** 系统返回 404 Not Found

### Requirement: 上传人物头像
系统 SHALL 提供独立的人像上传端点，支持替换已有头像。

#### Scenario: 为已有记录上传头像
- **WHEN** 客户端 `POST /api/v1/persons/1/avatar` 以 multipart/form-data 发送 `avatar=@new_face.jpg`
- **THEN** 系统保存图片到 `person_1/avatar.jpg`，更新 `avatar_path` 为 `person_1/avatar.jpg`，返回更新后的人物记录

#### Scenario: 为不存在的人物上传头像
- **WHEN** 客户端 `POST /api/v1/persons/99999/avatar`
- **THEN** 系统返回 404 Not Found

#### Scenario: 上传非图片文件
- **WHEN** 客户端上传的 avatar 文件不是 image/jpeg 或 image/png
- **THEN** 系统返回 422 验证错误，提示仅支持 JPEG/PNG
