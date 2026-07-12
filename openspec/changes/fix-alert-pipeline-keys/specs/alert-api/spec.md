# Alert API (Delta)

## MODIFIED Requirements

### Requirement: AlertResponse includes track_id and exception_name

告警响应 SHALL 包含 `track_id`（触发告警的ByteTrack跟踪ID）和 `exception_name`（异常规则名称）。

#### Scenario: Alert response with track info

- **WHEN** 前端请求告警列表
- **THEN** 每条告警包含 `track_id` 和 `exception_name` 字段

### Requirement: ExceptionDef CRUD includes cooldown_seconds

异常规则的创建和更新接口 SHALL 支持 `cooldown_seconds` 字段。

#### Scenario: Create exception with cooldown

- **WHEN** POST `/api/v1/exceptions/` 携带 `{"cooldown_seconds": 60, ...}`
- **THEN** 返回的 `ExceptionResponse` 包含 `cooldown_seconds: 60`
