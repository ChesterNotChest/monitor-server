## MODIFIED Requirements

### Requirement: 检测枚举管理
系统 SHALL 提供三类 AI 检测枚举（EntityType、ActionType、SoundType）的 CRUD 端点。负责人和运维员可访问。

- `GET/POST/PUT/DELETE /api/v1/detection/entity-types` — YOLO 实体类型
- `GET/POST/PUT/DELETE /api/v1/detection/action-types` — SlowFast 行为类型
- `GET/POST/PUT/DELETE /api/v1/detection/sound-types` — YAMNet 声音类型

#### Scenario: 运维员管理检测枚举
- **WHEN** 运维员调用 `POST /api/v1/detection/entity-types` 创建新实体类型
- **THEN** 权限检查通过，创建成功返回 201
