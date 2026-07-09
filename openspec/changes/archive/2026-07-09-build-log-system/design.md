## Context

异常/告警体系、人员管理、枚举管理、节点/设备/视图管理的 Model + Repo + Service + API 均已就绪。现在需要补充审计日志和用户身份基础设施。

## Goals / Non-Goals

**Goals:**
- User 最小模型（id, username, role），4 个固定角色：安全员/管理员/负责人/运维员
- LogEntry 统一日志表 + JSON 扩展字段，5 种日志类型
- LogService 统一写日志入口（各模块调用，不公开 Create API）
- 日志只读查询 + 统计 API

**Non-Goals:**
- 不做 JWT 认证/登录/权限校验（User 模型先建，API 后续可用）
- 日志不提供修改/删除（审计完整性）
- 不修改已有模块的代码（日志接入点后续 Change 分批加）

## Decisions

### 1. User 模型：最小化

**选择**: `id, username(unique), role(Enum)` 三个业务字段 + created_at。

```python
class UserRole(IntEnum):
    SECURITY = 1    # 安全员
    ADMIN = 2       # 管理员
    MANAGER = 3     # 负责人
    OPERATOR = 4    # 运维员
```

**理由**: 够用——日志记录 operator_id，告警处置记录 handler_id。不做密码/认证（后续独立 Change）。

### 2. LogEntry：统一表 + JSON 扩展

**选择**: 一张 `log_entries` 表，`log_type` 枚举 + `details_json` (Text/JSON) 存差异化信息。

| log_type | details_json 内容 |
|----------|------------------|
| DEVICE | device_type, device_id, device_name, event (online/offline) |
| OPERATION | action, target_type, target_id, target_name |
| RECOGNITION | model, detected, confidence, bbox |
| ALERT | action (confirm/close/escalate), event_id, comment |
| SYSTEM | event, message |

### 3. API：只读

```
GET  /api/v1/logs         查询 (log_type/view_id/operator_id/start/end/severity + 分页)
GET  /api/v1/logs/stats    统计 (group_by=log_type|severity)
GET  /api/v1/users         用户列表
POST /api/v1/users         创建用户
```

日志不开放 Create/Update/Delete——写入通过 `LogService.write()` 内部调用。

### 4. LogService 接口

```python
class LogService:
    @staticmethod
    def write(db, log_type, *, operator_id=None, view_id=None, event_id=None,
              severity=None, summary, details=None) -> LogEntry
```

各 Service 层在关键路径上调用 `LogService.write(db, ...)`。
