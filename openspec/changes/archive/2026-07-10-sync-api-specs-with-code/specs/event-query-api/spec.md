## MODIFIED Requirements

### Requirement: SituationEvent 查询
系统 SHALL 提供 SituationEvent（异常事件日志）的只读查询 API 与 Service，不提供创建/更新/删除（事件由 AI 检测引擎自动写入）。路由已在 `api/__init__.py` 中注册。

#### Scenario: 分页查询事件列表
- **WHEN** 客户端 `GET /api/v1/events`
- **THEN** 系统返回分页事件列表，按时间倒序，每条含 view/exception/timestamp 信息

#### Scenario: 按监控视图过滤
- **WHEN** 客户端 `GET /api/v1/events?view_id=1`
- **THEN** 系统仅返回该监控视图下的异常事件

#### Scenario: 查询单个事件详情
- **WHEN** 客户端 `GET /api/v1/events/1`
- **THEN** 系统返回该事件完整信息（含关联的 MonitorView 和 ExceptionDef）；不存在返回 404

### Requirement: 按异常分组统计
系统 SHALL 提供按 exception_id 分组的事件数量统计端点。

#### Scenario: 统计各异常类型的触发次数
- **WHEN** 客户端 `GET /api/v1/events/stats/by-exception`
- **THEN** 系统返回 `[{"exception_id": 1, "exception_severity": "CRITICAL", "count": 42}, ...]`

### Requirement: 按时间段趋势统计
系统 SHALL 提供按时间段粒度的事件趋势统计端点。

#### Scenario: 按天统计事件趋势
- **WHEN** 客户端 `GET /api/v1/events/stats/trend?granularity=day`
- **THEN** 系统返回 `[{"period": "2026-01-01", "count": 15}, ...]`

#### Scenario: 趋势统计默认按天聚合
- **WHEN** 客户端 `GET /api/v1/events/stats/trend`（不指定 granularity）
- **THEN** 系统默认按天（day）聚合
