# Electronic Fence Model

**Purpose:** 电子围栏模型的变更——新增围栏名称、View 绑定、密度/时限配置字段。coords 改为 JSON 类型，固定 4 点不规则四边形。

## MODIFIED Requirements

### Requirement: 电子围栏表定义

系统 SHALL 定义 `ElectronicFence` 模型，映射到 `electronic_fences` 表，存储围栏定义及其判定参数。

- `id`: 自增主键（Integer）
- `name`: 围栏名称（String，非空）
- `view_id`: 外键关联 `monitor_views.id`（Integer，非空，索引）
- `coords`: 围栏坐标点（JSON，非空），SHALL 包含恰好 4 个顶点，格式 `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]`，构成不规则四边形。坐标系为像素坐标系，与 YOLO bbox 同空间，左上角为原点
- `dwell_time`: 停留时限秒数（Integer，默认 10）
- `density`: 密度阈值（Float，默认 0.6，取值范围 0-1）
- `leave_frames`: 离开判定帧数（Integer，默认 5）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 创建四边形围栏

- **WHEN** 插入围栏记录提供 name、view_id、恰好 4 个顶点的 coords、dwell_time、density、leave_frames
- **THEN** 系统持久化围栏数据，后续可通过 `view_id` 查询该 View 下所有围栏

#### Scenario: coords 点数校验

- **WHEN** 创建围栏时 coords 不足或超过 4 个顶点
- **THEN** 系统拒绝写入，返回 422 校验错误

#### Scenario: 默认参数

- **WHEN** 创建围栏时未提供 dwell_time、density、leave_frames
- **THEN** 系统使用默认值（10、0.6、5）

#### Scenario: 坐标空间

- **WHEN** 围栏 coords 为 `[[100,200], [500,200], [500,400], [100,400]]`
- **THEN** 像素坐标系（左上角为原点），与 YOLO person_bbox 同空间，可直接做 IoU 计算
