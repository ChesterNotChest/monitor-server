# Electronic Fence Model — Delta

## MODIFIED Requirements

### Requirement: 电子围栏表定义
系统 SHALL 定义 `ElectronicFence` 模型，映射到 `electronic_fences` 表，存储地理围栏的坐标数据及检测参数。

- `id`: 自增主键（Integer）
- `coords`: 围栏坐标点（Text，非空），以 JSON 字符串格式存储多边形顶点数组 `[[x, y], ...]`
- `safe_distance`: 安全距离（Integer，默认 0），像素值，表示围栏各边向外平移的距离。0 = 禁用 TOO_CLOSE 检测
- `entry_delay_seconds`: 进入延时（Integer，默认 0），秒数。0 = Track 进入即触发 ENTERED；>0 = 连续停留该秒数后触发

#### Scenario: 创建多边形围栏
- **WHEN** 插入记录提供多边形顶点坐标 JSON 字符串
- **THEN** 系统持久化围栏数据，后续可通过 `id` 查询和回显坐标

#### Scenario: 创建带安全距离的围栏
- **WHEN** 插入记录时指定 `safe_distance=50`
- **THEN** 围栏检测引擎计算扩展多边形并在 Track 靠近时触发 TOO_CLOSE 事件

#### Scenario: 创建带进入延时的围栏
- **WHEN** 插入记录时指定 `entry_delay_seconds=3`
- **THEN** Track 进入围栏后需连续停留 3 秒才触发 ENTERED 事件
