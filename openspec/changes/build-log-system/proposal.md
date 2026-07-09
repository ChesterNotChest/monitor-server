## Why

系统当前没有任何审计日志能力。设备的上下线、管理员的增删改操作、AI 识别结果、告警处置动作——这些都需要被记录下来形成可追溯的日志链。User 模型也是空白，日志中的 `operator_id` 和后续告警处置的 `handler_id` 都依赖它。

## What Changes

- 新增 `User` 模型（最小化：id, username, role）— 顺手建，供日志和告警处置引用
- 新增 `LogEntry` 模型：统一日志表，按 `log_type` 分类，JSON 扩展字段存差异化信息
- 新增 `LogService` — 各模块在关键路径上调用的写日志入口
- 新增日志查询与统计 API（只读，不提供修改/删除）
- 日志类型：DEVICE（设备状态）、OPERATION（用户操作）、RECOGNITION（AI 识别）、ALERT（告警处置）、SYSTEM（系统事件）

## Capabilities

### New Capabilities

- `log-system`: 统一分类日志系统 — LogEntry 模型 + 写入 Service + 查询/统计 API
- `user-model`: User 最小模型（username + role）— 基础设施，供日志和告警处置共用

### Modified Capabilities

<!-- 无 — 纯增量 -->

## Impact

- **新增**: `models/user.py`、`models/log_entry.py`、`repository/user_repo.py`、`repository/log_entry_repo.py`
- **新增**: `service/log_task.py`（写日志 + 查日志 + 统计）
- **新增**: `schema/http/log.py`、`schema/http/user.py`
- **新增**: `network/api/log.py`、`network/api/user.py`
- **不修改**任何现有代码
