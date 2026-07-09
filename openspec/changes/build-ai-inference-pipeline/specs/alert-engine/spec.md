# Alert Engine

**Purpose:** ExceptionDef 规则匹配引擎——活跃枚举事件集合 ⊇ 规则要求 → 告警触发（SituationEvent + AlertGroup）。

## ADDED Requirements

### Requirement: ExceptionDef 匹配

系统 SHALL 每 `ALERT_CHECK_INTERVAL` 秒（默认 5 秒）检查一次当前活跃的枚举事件集合是否覆盖任何 ExceptionDef 的全部要求。覆盖则触发——所有关联的 EntityType、ActionType、SoundType、FaceResult、FenceEvent 必须同时满足（AND 逻辑）。

#### Scenario: 全部条件满足触发

- **WHEN** 当前活跃：EntityType.PERSON + ActionType.FIGHTING + SoundType.SCREAM
- **AND** ExceptionDef "FIGHTING" 绑定此三项
- **THEN** 触发告警，创建 SituationEvent

#### Scenario: 部分条件不触发

- **WHEN** 当前活跃：EntityType.PERSON + ActionType.FIGHTING（无 SoundType.SCREAM）
- **AND** ExceptionDef "FIGHTING" 绑定三项
- **THEN** 不触发

### Requirement: 同异常去重——不重复写，但保持录制

系统 SHALL 对同一 `(view_id, exception_def_id)` 的重复触发做去重：在 `ALERT_COOLDOWN` 秒（默认 30 秒）内，同一规则再次触发 SHALL NOT 创建新的 SituationEvent，但 SHALL 通过 EventBus 通知录制系统"仍有异常活动"，阻止录制因空闲而终止。

#### Scenario: 同异常在冷却期内再次触发

- **WHEN** ExceptionDef "FIGHTING" 在 T 时刻触发，T+10s 再次满足条件
- **AND** `ALERT_COOLDOWN=30s`
- **THEN** 不创建第二条 SituationEvent
- **AND** 通知录制系统保持活跃（重置空闲倒计时）

#### Scenario: 同异常冷却期过后再次触发

- **WHEN** ExceptionDef "FIGHTING" 在 T 时刻触发，T+35s 再次满足条件
- **AND** `ALERT_COOLDOWN=30s`（已过冷却期）
- **THEN** 创建第二条 SituationEvent

### Requirement: 异异常独立触发

不同 ExceptionDef SHALL 独立触发。同一时间窗口内，规则 A 触发不抑制规则 B。

#### Scenario: 两个不同规则同时触发

- **WHEN** ExceptionDef "FIGHTING" 和 "INTRUDER" 的条件同时满足
- **THEN** 两条规则各自创建 SituationEvent，互不干扰

### Requirement: EventBus 订阅与事件过期

告警引擎 SHALL 订阅 EventBus 的全部事件类型。收到事件后 SHALL 更新内存中的活跃事件集合。事件在 `ALERT_EVENT_TTL`（默认 5 秒）后自动过期。

> 注：围栏事件（FenceEvent）的 ENTERED 状态由围栏状态机（`fence_engine`）维护，告警引擎将 ENTERED 视为一个持续活跃的状态（而非瞬时事件）。围栏状态机在判定离开时从 EventBus 发布 ENTERED 清除事件。

#### Scenario: 事件过期

- **WHEN** EntityType.PERSON 事件写入时间 > ALERT_EVENT_TTL
- **THEN** 从活跃集合中移除

### Requirement: 录制信号

告警引擎 SHALL 在每次任一 ExceptionDef 触发时（无论是否被去重抑制），向 EventBus topic `RECORDING` publish `{"action": "keep_alive", "view_id": ...}`。录制系统据此重置空闲倒计时。

#### Scenario: 连续同异常延长录制

- **WHEN** ExceptionDef "FIGHTING" 连续 3 次检查窗口都满足条件
- **THEN** 第一条写 SituationEvent，后两条仅发 keep_alive → 录制持续不中断

### Requirement: 全链路集成——从枚举事件到响应动作

系统 SHALL 在集成测试中验证完整告警链路：枚举事件 → ExceptionDef 匹配 → SituationEvent 写入 → AlertGroup 查询 → ResponseAction 执行。

#### Scenario: 全链路触发——FIGHTING 规则

- **GIVEN** 已创建 ExceptionDef "FIGHTING"（severity=CRITICAL，绑定 EntityType.PERSON + ActionType.FIGHTING，关联 AlertGroup "security-alert"），AlertGroup 配置了 ResponseAction.TRIGGER_RECORDING
- **WHEN** EventBus 同时收到 `ENTITY(PERSON)` 和 `ACTION(FIGHTING)` 事件
- **THEN** AlertEngine 匹配成功 → `SituationEvent(view_id, exception_id)` 写入 DB → 查询 `exception.group_id` → AlertGroup "security-alert" → 触发 `TRIGGER_RECORDING` 响应动作 → 录制系统收到 keep_alive 信号

#### Scenario: 全链路触发——INTRUDER 规则

- **GIVEN** 已创建 ExceptionDef "INTRUDER"（severity=WARNING，绑定 FenceEventType.ENTERED，关联 AlertGroup "fence-alert"），AlertGroup 配置了 ResponseAction.SEND_NOTIFICATION
- **WHEN** FenceEngine 发布 `FENCE(ENTERED)` 事件
- **THEN** 链路上所有环节正常执行：ENTERED → ExceptionDef 匹配 → SituationEvent → AlertGroup → ResponseAction

#### Scenario: 不满足条件——链路静默

- **GIVEN** 同上的 ExceptionDef "FIGHTING"
- **WHEN** EventBus 只收到 `ENTITY(PERSON)` 事件（无 FIGHTING）
- **THEN** 不触发，不写 SituationEvent，不触发 ResponseAction，录制系统不收到 keep_alive

#### Scenario: 多规则独立触发

- **GIVEN** 两条 ExceptionDef："FIGHTING" 和 "INTRUDER"，各自绑定不同的 AlertGroup
- **WHEN** EventBus 同时满足两条规则的条件
- **THEN** 两条 SituationEvent 各自写入，两个 AlertGroup 各自触发，各自的 ResponseAction 各自执行，互不干扰

### Requirement: HTTP API 层集成——从规则创建到告警查询

系统 SHALL 在集成测试中验证从前端 HTTP API 到告警产出的完整链路。测试 SHALL 使用 `httpx.TestClient`，无需真实 RTMP/FFmpeg/SRS。

#### Scenario: 创建规则到告警产出

- **GIVEN** 测试 DB 中有 EntityType(id=1,PERSON)、ActionType(id=1,FIGHTING)、AlertGroup "security"
- **WHEN** 前端调用 `POST /api/v1/exceptions` 创建 FIGHTING 规则（绑定 PERSON + FIGHTING + AlertGroup "security"）
- **AND** 前端调用 `POST /api/v1/views` 创建 View
- **AND** AlertEngine 收到 EventBus 双事件
- **THEN** `GET /api/v1/alerts` 返回非空列表，包含新触发的 FIGHTING 告警
- **AND** 告警记录包含 `view_id`、`exception_name`、`severity`、`timestamp`

#### Scenario: 处理告警

- **GIVEN** 已有触发的 FIGHTING 告警
- **WHEN** `PUT /api/v1/alerts/{alert_id}/handle`
- **THEN** 告警状态变更为已处理，后续 `GET /api/v1/alerts` 过滤掉已处理的告警

#### Scenario: 无告警时的平静状态

- **GIVEN** 无任何枚举事件活跃
- **WHEN** `GET /api/v1/alerts`
- **THEN** 返回空列表或无未处理告警
