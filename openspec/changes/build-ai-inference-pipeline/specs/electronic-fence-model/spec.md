# Electronic Fence Model

**Purpose:** 电子围栏模型的变更——新增围栏名称、View 绑定、密度/时限配置字段。

## MODIFIED Requirements

### Requirement: 电子围栏表定义

系统 SHALL 定义 `ElectronicFence` 模型，映射到 `electronic_fences` 表，存储围栏定义及其判定参数。

- `id`: 自增主键（Integer）
- `name`: 围栏名称（String，非空）
- `view_id`: 外键关联 `monitor_views.id`（Integer，非空，索引）
- `coords`: 围栏坐标点（Text，非空），以 JSON 字符串格式存储多边形顶点数组 `[[x1, y1], [x2, y2], ...]`
- `dwell_time`: 停留时限秒数（Integer，默认 10）
- `density`: 密度阈值（Float，默认 0.6，取值范围 0-1）
- `leave_frames`: 离开判定帧数（Integer，默认 5）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 创建围栏

- **WHEN** 插入围栏记录提供 name、view_id、coords、dwell_time、density、leave_frames
- **THEN** 系统持久化围栏数据，后续可通过 `view_id` 查询该 View 下所有围栏

#### Scenario: 默认参数

- **WHEN** 创建围栏时未提供 dwell_time、density、leave_frames
- **THEN** 系统使用默认值（10、0.6、5）
