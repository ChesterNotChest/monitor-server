# Delta: View Management — 车辆旁路生命周期

## ADDED Requirements

### Requirement: 车辆旁路随 View 管线启动

系统 SHALL 在 View 的 AI 管线启动时自动创建并注册 `VehicleProcessor` 实例。`VehicleProcessor` SHALL 与 View 的 AI 管线共享生命周期——管线启动时初始化统计状态，管线停止时丢弃。

#### Scenario: 创建 View 自动启动车辆旁路

- **WHEN** 通过 `POST /api/v1/views/` 创建新 View 且 AI 管线启动
- **THEN** `VehicleProcessor` 实例随管线一同创建
- **AND** 车辆统计状态初始化为零

#### Scenario: Server 重启恢复车辆旁路

- **WHEN** Server 重启后 `app.py` 的 startup 事件恢复已有 View 的管线
- **THEN** 每个恢复的 View 自动创建新的 `VehicleProcessor` 实例
- **AND** 车辆统计从零开始（不保留重启前的统计）

#### Scenario: 删除 View 停止车辆旁路

- **WHEN** 通过 `DELETE /api/v1/views/{view_id}` 删除 View
- **THEN** 对应的 `VehicleProcessor` 实例随管线一同释放
- **AND** 车辆统计数据被丢弃
