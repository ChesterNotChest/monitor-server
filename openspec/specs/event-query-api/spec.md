# Event Query API

**Purpose:** 定义 SituationEvent 事件日志的只读查询 API 与 Service，支持按 view 过滤、按时间范围过滤、按 exception 分组 count 聚合、按时间段趋势统计。

## Requirements

### Requirement: SituationEvent 查询
系统 SHALL 提供 SituationEvent（异常事件日志）的只读查询 API 与 Service，不提供创建/更新/删除（事件由 AI 检测引擎自动写入）。

#### Scenario: 分页查询事件列表
- **WHEN** 客户端 `GET /api/v1/events`
- **THEN** 系统返回分页事件列表，按时间倒序，每条含 view/excption/timestamp 信息

#### Scenario: 按监控视图过滤
- **WHEN** 客户端 `GET /api/v1/events?view_id=1`
- **THEN** 系统仅返回该监控视图下的异常事件

#### Scenario: 按时间范围过滤
- **WHEN** 客户端 `GET /api/v1/events?start=2026-01-01T00:00:00&end=2026-01-02T00:00:00`
- **THEN** 系统仅返回该时间区间内的事件

#### Scenario: 查询单个事件详情
- **WHEN** 客户端 `GET /api/v1/events/1`
- **THEN** 系统返回该事件完整信息（含关联的 MonitorView 和 ExceptionDef）

### Requirement: 按异常分组统计
系统 SHALL 提供按 exception_id 分组的事件数量统计端点。

#### Scenario: 统计各异常类型的触发次数
- **WHEN** 客户端 `GET /api/v1/events/stats/by-exception`
- **THEN** 系统返回 `[{"exception_id": 1, "exception_severity": "CRITICAL", "count": 42}, ...]`

#### Scenario: 统计带时间范围过滤
- **WHEN** 客户端 `GET /api/v1/events/stats/by-exception?start=2026-01-01&end=2026-01-07`
- **THAN** 系统仅统计该时间范围内的事件

### Requirement: 按时间段趋势统计
系统 SHALL 提供按时间段粒度的事件趋势统计端点。

#### Scenario: 按天统计事件趋势
- **WHEN** 客户端 `GET /api/v1/events/stats/trend?granularity=day&start=2026-01-01&end=2026-01-07`
- **THEN** 系统返回 `[{"period": "2026-01-01", "count": 15}, {"period": "2026-01-02", "count": 23}, ...]`

#### Scenario: 按小时统计事件趋势
- **WHEN** 客户端 `GET /api/v1/events/stats/trend?granularity=hour&start=2026-01-01T00:00:00&end=2026-01-01T23:59:59`
- **THEN** 系统返回每小时的事件数量 `[{"period": "2026-01-01T00", "count": 3}, ...]`

#### Scenario: 趋势统计默认按天聚合
- **WHEN** 客户端 `GET /api/v1/events/stats/trend`（不指定 granularity）
- **THEN** 系统默认按天（day）聚合最近 7 天的事件
