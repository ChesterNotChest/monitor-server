## Purpose

提供组 B（人员、告警与事件）的 Repository 层。涵盖命名人物、告警分组、异常定义、响应动作及异常事件的数据访问。

## Requirements

### Requirement: NamedPersonRepo
系统 SHALL 定义 `NamedPersonRepo(BaseRepo[NamedPerson])`，提供命名人物数据访问。

- `model = NamedPerson`

### Requirement: AlertGroupRepo
系统 SHALL 定义 `AlertGroupRepo(BaseRepo[AlertGroup])`，提供告警分组数据访问。

- `model = AlertGroup`
- 特有方法 `with_responses() -> list[AlertGroup]`：查询所有告警分组及其关联的响应动作（eager load `responses` 关系）

#### Scenario: 查询告警分组及其响应动作
- **WHEN** 调用 `group_repo.with_responses()`
- **THEN** 返回所有 AlertGroup，每个实例的 `responses` 属性已预加载

### Requirement: ExceptionDefRepo
系统 SHALL 定义 `ExceptionDefRepo(BaseRepo[ExceptionDef])`，提供异常定义数据访问。

- `model = ExceptionDef`
- 特有方法 `by_severity(severity: SeverityLevel) -> list[ExceptionDef]`：按严重级别过滤
- 特有方法 `by_group(group_id: int) -> list[ExceptionDef]`：按告警分组过滤
- 特有方法 `with_details() -> list[ExceptionDef]`：eager load 所有关联（entities/actions/sounds/alert_group）

#### Scenario: 按严重级别查询异常
- **WHEN** 调用 `exception_repo.by_severity(SeverityLevel.CRITICAL)`
- **THEN** 返回所有严重级别为 CRITICAL 的异常定义

#### Scenario: 按告警分组查询异常
- **WHEN** 调用 `exception_repo.by_group(group_id=1)`
- **THEN** 返回该分组下所有异常定义

#### Scenario: 查询异常及完整关联
- **WHEN** 调用 `exception_repo.with_details()`
- **THEN** 返回所有异常定义，每个实例的 `entities`、`actions`、`sounds`、`alert_group` 已预加载

### Requirement: ResponseActionRepo
系统 SHALL 定义 `ResponseActionRepo(BaseRepo[ResponseAction])`，提供响应动作数据访问。

- `model = ResponseAction`
- 特有方法 `with_groups() -> list[ResponseAction]`：查询所有响应动作及其关联的告警分组

#### Scenario: 查询响应动作及关联分组
- **WHEN** 调用 `response_repo.with_groups()`
- **THEN** 返回所有 ResponseAction，每个实例的 `alert_groups` 属性已预加载

### Requirement: SituationEventRepo
系统 SHALL 定义 `SituationEventRepo(BaseRepo[SituationEvent])`，提供异常事件数据访问。

- `model = SituationEvent`
- 特有方法 `by_view(view_id: int) -> list[SituationEvent]`：按监控视图查询
- 特有方法 `by_time_range(start, end) -> list[SituationEvent]`：按时间范围查询

#### Scenario: 按视图查询事件
- **WHEN** 调用 `event_repo.by_view(view_id=1)`
- **THEN** 返回该视图下所有异常事件，按时间倒序

#### Scenario: 按时间范围查询事件
- **WHEN** 调用 `event_repo.by_time_range(start=datetime_a, end=datetime_b)`
- **THEN** 返回在 `[start, end]` 时间区间内的所有事件
