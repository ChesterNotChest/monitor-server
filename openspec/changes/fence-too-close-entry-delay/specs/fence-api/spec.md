# Fence API — Delta

## MODIFIED Requirements

### Requirement: 电子围栏 CRUD
系统 SHALL 提供电子围栏的完整 CRUD 端点。仅安全员可访问。

- `GET /api/v1/fences` — 列出所有电子围栏（响应含 `safe_distance`、`entry_delay_seconds`）
- `POST /api/v1/fences` — 创建电子围栏（请求体可选 `safe_distance`、`entry_delay_seconds`，默认均为 0）
- `PUT /api/v1/fences/{id}` — 更新围栏（含可选 `safe_distance`、`entry_delay_seconds` 更新）
- `DELETE /api/v1/fences/{id}` — 删除围栏

#### Scenario: 创建围栏含安全距离
- **WHEN** 安全员 POST `/api/v1/fences` 携带 `safe_distance=50`
- **THEN** 系统创建围栏并返回含 `safe_distance: 50` 的响应

#### Scenario: 创建围栏含进入延时
- **WHEN** 安全员 POST `/api/v1/fences` 携带 `entry_delay_seconds=3`
- **THEN** 系统创建围栏并返回含 `entry_delay_seconds: 3` 的响应

#### Scenario: 字段缺省
- **WHEN** 安全员 POST `/api/v1/fences` 不传 `safe_distance` 和 `entry_delay_seconds`
- **THEN** 系统以默认值 0 创建围栏，行为与原有二元检测一致
