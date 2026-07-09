# Detection Enum API

**Purpose:** YOLO 实体类型、SlowFast 行为类型、YAMNet 声音类型的枚举 CRUD——仅负责人可访问。

## Requirements

### Requirement: 检测枚举管理
系统 SHALL 提供三类 AI 检测枚举（EntityType、ActionType、SoundType）的 CRUD 端点。仅负责人可访问。

- `GET/POST/PUT/DELETE /api/v1/detection/entity-types` — YOLO 实体类型
- `GET/POST/PUT/DELETE /api/v1/detection/action-types` — SlowFast 行为类型
- `GET/POST/PUT/DELETE /api/v1/detection/sound-types` — YAMNet 声音类型
