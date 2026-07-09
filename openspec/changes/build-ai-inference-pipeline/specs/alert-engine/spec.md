# Alert Engine

**Purpose:** ExceptionDef 规则匹配引擎——活跃枚举事件集合 ⊇ 规则要求 → 告警触发（SituationEvent + AlertGroup）。

## ADDED Requirements

### Requirement: ExceptionDef 匹配

系统 SHALL 每 5 秒（`ALERT_CHECK_INTERVAL`）检查一次当前活跃的枚举事件集合是否覆盖任何 ExceptionDef 的全部要求。覆盖则触发——所有关联的 EntityType、ActionType、SoundType、FaceResult、FenceEvent 必须同时满足。

#### Scenario: 全部条件满足触发

- **WHEN** 当前活跃：EntityType.PERSON + ActionType.FIGHTING + SoundType.SCREAM
- **AND** ExceptionDef "FIGHTING" 绑定此三项
- **THEN** 触发告警

#### Scenario: 部分条件不触发

- **WHEN** 当前活跃：EntityType.PERSON + ActionType.FIGHTING（无 SoundType.SCREAM）
- **AND** ExceptionDef "FIGHTING" 绑定三项
- **THEN** 不触发

### Requirement: 去重

系统 SHALL 用 `(view_id, exception_def_id, timestamp // ALERT_CHECK_INTERVAL)` 去重。同一规则在同一时间窗口内 SHALL 不重复触发。

#### Scenario: 连续帧去重

- **WHEN** ExceptionDef "FIGHTING" 在窗口 T 已触发
- **AND** 窗口 T+1（5s 后）条件仍满足
- **THEN** 窗口 T+1 再次触发（不同窗口），写入第二条 SituationEvent

### Requirement: EventBus 订阅

告警引擎 SHALL 订阅 EventBus 的全部事件类型。收到事件后 SHALL 更新内存中的活跃事件集合。事件在 `ALERT_EVENT_TTL`（默认 5 秒）后自动过期。

#### Scenario: 事件过期

- **WHEN** EntityType.PERSON 事件写入时间 > ALERT_EVENT_TTL
- **THEN** 从活跃集合中移除
