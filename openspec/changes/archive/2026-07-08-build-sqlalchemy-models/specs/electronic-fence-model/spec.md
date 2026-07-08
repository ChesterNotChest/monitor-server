## ADDED Requirements

### Requirement: 电子围栏表定义
系统 SHALL 定义 `ElectronicFence` 模型，映射到 `electronic_fences` 表，存储地理围栏的坐标数据。

- `id`: 自增主键（Integer）
- `coords`: 围栏坐标点（Text，非空），以 JSON 字符串格式存储多边形顶点数组 `[[lon, lat], ...]`

#### Scenario: 创建多边形围栏
- **WHEN** 插入记录提供多边形顶点坐标 JSON 字符串
- **THEN** 系统持久化围栏数据，后续可通过 `id` 查询和回显坐标
