# Fence Too Close

## Purpose

在围栏原始多边形外扩展 `safe_distance` 像素缓冲区，当 YOLO 框与扩展多边形交错但未接触原始多边形时，触发 `TOO_CLOSE` 告警事件。

## ADDED Requirements

### Requirement: Safe distance buffer around fence

`ElectronicFence` 模型 SHALL 包含 `safe_distance` 字段（像素，整数，默认 0=禁用）。
fence_engine SHALL 以原始围栏多边形为基础向外扩展 `safe_distance` 像素得到扩展多边形。

#### Scenario: Safe distance configured

- **WHEN** 用户创建围栏并设置 `safe_distance=50`
- **THEN** fence_engine 计算原始多边形向外 50 像素的扩展多边形

### Requirement: TOO_CLOSE state detection

fence_engine SHALL 在每个检测帧检查 YOLO 框是否与扩展多边形交错。
当 YOLO 框与扩展多边形交错但**未**接触原始多边形时，SHALL 发布 `TOO_CLOSE` 事件。
`FenceEventResult` 枚举 SHALL 包含 `TOO_CLOSE = 2`。

#### Scenario: Person near fence but not inside

- **WHEN** YOLO 检测到人物 bbox 距离围栏 30 像素（小于 `safe_distance=50`），但未进入围栏
- **THEN** fence_engine 发布 TOO_CLOSE 事件

#### Scenario: safe_distance=0 disables TOO_CLOSE

- **WHEN** `safe_distance=0`
- **THEN** 不发布 TOO_CLOSE 事件

### Requirement: TOO_CLOSE triggers alert

AlertEngine SHALL 识别 `TOO_CLOSE` 事件并匹配 `ExceptionDef` 规则，
创建 `SituationEvent` 并推送告警。

#### Scenario: TOO_CLOSE alert pushed

- **WHEN** TOO_CLOSE 事件发布且存在匹配的 `ExceptionDef`
- **THEN** 前端收到含 `fence_event_id` 的告警
