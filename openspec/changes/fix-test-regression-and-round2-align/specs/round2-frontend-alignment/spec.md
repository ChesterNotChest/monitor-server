# Round 2 Frontend-Backend Alignment

## Purpose

以前端已实现的 API 调用代码为基准，对照 Swagger (`/docs`) 和 server 代码，逐模块验证前后端一致。发现不一致时，前端迁就后端。

## ADDED Requirements

### Requirement: Auth module alignment

前端 `AuthContext.tsx` 中的 login/logout/me 调用 SHALL 与 server `auth_router.py` 的请求参数、响应结构一致。`UserResponse` 字段（id, username, role, is_active）SHALL 被正确解析。

#### Scenario: Login returns correct UserResponse

- **WHEN** 前端调用 `POST /auth/login`
- **THEN** `LoginResponse.user` 的字段 id, username, role (string), is_active SHALL 被正确提取

### Requirement: View module alignment

前端 `LiveMonitor.tsx` 中的视图创建/查询调用 SHALL 匹配当前 server `view_router.py` 的扁平 `ViewResponse` 格式。

#### Scenario: View create response is parsed correctly

- **WHEN** 前端调用 `POST /views` 创建视图
- **THEN** 前端能正确解析 `ViewResponse` 的扁平字段（id, audio_id, video_id, flv_url, webrtc_url, rtmp_url, warnings）
- **AND** 不需要从嵌套的 `["view"]` 中提取

### Requirement: Fence module alignment

前端 `FenceEditor.tsx` 中的 FenceCreate 请求 SHALL 包含全部必填字段：name, view_id, coords (number[][]), dwell_time, density, leave_frames。

#### Scenario: Fence create sends all required fields

- **WHEN** 前端创建电子围栏
- **THEN** 请求体 SHALL 包含 name, view_id, coords, dwell_time, density, leave_frames
- **AND** coords SHALL 为 `number[][]` 格式（非 string）

### Requirement: Exception module alignment

前端 `ExceptionSettings.tsx` 中的 ExceptionCreate 请求 SHALL 使用 `group_id`（非 `alert_group_id`），并包含 face_result_id 和 fence_event_id 可选字段。

#### Scenario: Exception create uses group_id

- **WHEN** 前端创建异常规则
- **THEN** 请求体 SHALL 使用 `group_id` 字段名（非 `alert_group_id`）

### Requirement: User management module alignment

前端 `UserManagement.tsx` SHALL 区分两个 UserResponse 版本：auth 版（role: string, is_active）和 user CRUD 版（role: int, created_at）。

#### Scenario: User list parses correct role type

- **WHEN** 前端调用 `GET /users` 获取用户列表
- **THEN** role 字段 SHALL 被解析为整数（1-4），按需映射为角色名

### Requirement: All frontend API calls match Swagger

前端 `client.ts` 中的全部 API 函数 SHALL 在 HTTP method、path、query params、request body、response type 上与 Swagger 声明一致。所有差异 SHALL 被记录并修复。

#### Scenario: No endpoint mismatch

- **WHEN** 逐一对比前端 client.ts 函数与 Swagger 对应端点
- **THEN** 每个函数的 method、path、参数与 Swagger 一致
- **AND** 不一致项被记录在 issues 列表中
