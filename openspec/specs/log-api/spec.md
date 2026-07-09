# Log API

**Purpose:** 系统日志查看——仅运维员可访问。

## Requirements

### Requirement: 系统日志查看
系统 SHALL 提供日志查询端点，支持分页和按级别/时间范围筛选。仅运维员可访问。

- `GET /api/v1/logs` — 日志列表（分页 + filter）
- `GET /api/v1/logs/{id}` — 单条日志详情

日志来源 SHALL 包括 application 日志（Python logging 模块输出）和 system 日志（Node 状态变更、设备上下线等写入 DB 的结构化记录）。
