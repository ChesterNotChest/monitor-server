# View Management

## API Contract Delta

### Requirement: View creation uses a JSON request body

The system SHALL expose `POST /api/v1/views` with a JSON request body modeled
by `ViewCreateRequest`. The request body SHALL contain `audio_id` and
`video_id`. These fields SHALL NOT be query parameters, so Swagger and frontend
clients see the same contract.

#### Scenario: Swagger documents view creation input

- **WHEN** a frontend developer opens `POST /api/v1/views` in Swagger
- **THEN** `audio_id` and `video_id` are shown as JSON request body fields

#### Scenario: View creation request

- **WHEN** the client posts `{"audio_id": 1, "video_id": 1}` to
  `/api/v1/views`
- **THEN** Server creates the View using those device ids

**Purpose:** 监控视图的 CRUD——前端选择 audio+video 组成 View，Server 管理流生命周期。

## ADDED Requirements

### Requirement: 创建监控视图

系统 SHALL 提供 `POST /api/v1/views` 接口，接收 `{audio_id, video_id}` 参数。创建时 SHALL 检查 audio 和 video 的引用计数——若引用计数为零，SHALL 通过 WSS 向对应 Node 发送 `UPDATE_STREAM` 命令启动推流；若引用计数大于零，SHALL 在响应中返回告警信息（"该流已被 N 个 View 使用"）。创建成功后 SHALL 启动 FFmpeg 合并流程推流到 SRS。

#### Scenario: 创建 View 并触发新推流

- **WHEN** 前端请求 `POST /api/v1/views` 提供 `{audio_id: 1, video_id: 1}`，且 audio 和 video 均未被其他 View 使用
- **THEN** Server 发送两条 `UPDATE_STREAM {device_type, device_id, enable=true}` 命令到对应 Node，创建 View 记录，启动 FFmpeg 合并推流到 SRS，返回 View 详情（含 SRS 拉流地址）

#### Scenario: 创建 View 但流已被其他 View 使用

- **WHEN** 前端请求创建 View 使用已被其他 View 引用的流
- **THEN** Server 不发送 `UPDATE_STREAM`，创建 View 记录，启动新的 FFmpeg 合并，返回 View 详情和告警信息

#### Scenario: 创建 View 时设备不存在

- **WHEN** 前端请求 `POST /api/v1/views` 提供的 `audio_id` 或 `video_id` 在数据库中不存在
- **THEN** Server 返回 404 错误

### Requirement: 删除监控视图

系统 SHALL 提供 `DELETE /api/v1/views/{view_id}` 接口。操作顺序 SHALL 为：先删除数据库中的 View 记录（事务保护），成功后再终止该 View 对应的 FFmpeg 子进程（失败则仅记录日志、不影响 DB 一致性），最后检查 audio 和 video 的引用计数——若某设备的引用计数归零，SHALL 通过 WSS 向对应 Node 发送 `UPDATE_STREAM=false` 命令停止推流。

#### Scenario: 删除 View 且流不再被使用

- **WHEN** 前端请求 `DELETE /api/v1/views/{view_id}`，且该 View 的 audio 和 video 均无其他 View 引用
- **THEN** Server 先删除 View 记录，再终止 FFmpeg 进程，最后发送两条 `UPDATE_STREAM {device_type, device_id, enable=false}` 到对应 Node，返回成功

#### Scenario: 删除 View 但流仍被其他 View 使用

- **WHEN** 前端请求 `DELETE /api/v1/views/{view_id}`，且该 View 的 audio 或 video 仍有其他 View 引用
- **THEN** Server 先删除 View 记录，再终止该 View 的 FFmpeg 进程，不发送 `UPDATE_STREAM=false`，返回成功

#### Scenario: 删除 View 时 FFmpeg 进程已不存在

- **WHEN** 删除 View 时 FFmpeg 子进程已经异常退出
- **THEN** Server 正常删除 DB 记录，记录警告日志，引用计数判断正常进行

### Requirement: 查询 View 列表

系统 SHALL 提供 `GET /api/v1/views` 接口，返回所有 View 的列表，SHALL 包含 SRS 拉流地址以便前端直接播放。

#### Scenario: 查询所有 View

- **WHEN** 前端请求 `GET /api/v1/views`
- **THEN** 返回 View 列表，每个 View 包含 `id`、`video_id`、`audio_id`、`cache_path`、`srs_play_url`、`created_at`

### Requirement: 查询单个 View 详情

系统 SHALL 提供 `GET /api/v1/views/{view_id}` 接口，返回指定 View 的详细信息，SHALL 包含关联的 VideoDevice 和 AudioDevice 详情。

#### Scenario: 查询指定 View

- **WHEN** 前端请求 `GET /api/v1/views/{view_id}`
- **THEN** 返回 View 详情，包含关联的 video device 和 audio device 信息、SRS 拉流地址、创建时间

### Requirement: View lifecycle changes are transactionally durable

The View service SHALL explicitly commit successful create/delete lifecycle
changes and SHALL roll back the active database session when an exception
prevents completion.

#### Scenario: Created View is visible after request completion

- **WHEN** `POST /api/v1/views` returns success
- **THEN** a subsequent `GET /api/v1/views` SHALL include the created View
- **AND** the referenced devices SHALL keep their updated `streaming` state

#### Scenario: Delete View commits release state

- **WHEN** `DELETE /api/v1/views/{view_id}` returns success
- **THEN** a subsequent `GET /api/v1/views/{view_id}` SHALL return 404
- **AND** devices whose reference count reached zero SHALL keep `streaming=false`

#### Scenario: Lifecycle operation fails

- **WHEN** View creation or deletion raises before returning a response
- **THEN** Server SHALL roll back the database session before propagating the error
