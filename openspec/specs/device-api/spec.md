# Device API

**Purpose:** 设备列表、健康状态、设备接入——仅运维员可访问。

## Requirements

### Requirement: 设备列表
系统 SHALL 提供 `GET /api/v1/devices/nodes` 端点。返回所有 Node 列表，含 `is_connected` 和 `last_seen`。仅运维员可访问。

### Requirement: 设备健康
系统 SHALL 提供 `GET /api/v1/devices/nodes/{id}/health` 端点。返回指定 Node 的健康摘要：在线状态、关联设备数、推流中的设备数。仅运维员可访问。

### Requirement: 设备接入
系统 SHALL 提供 `POST /api/v1/devices/nodes/{id}/onboard` 端点。触发新设备发现流程。仅运维员可访问。
