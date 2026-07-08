## Purpose

提供组 A（设备管理与 AI 枚举）的 Repository 层。涵盖计算机节点、视频/音频采集设备、监控视图、电子围栏及三类 AI 检测枚举（YOLO 实体、SlowFast 行为、YAMNet 声音）的数据访问。

## Requirements

### Requirement: NodeRepo
系统 SHALL 定义 `NodeRepo(BaseRepo[Node])`，提供节点数据访问。

- `model = Node`
- 特有方法 `by_token(token: str) -> Node | None`：按认证令牌查找节点

#### Scenario: 按 token 查找节点
- **WHEN** 调用 `node_repo.by_token("abc123")`
- **THEN** 返回匹配的 Node 实例，或 `None`

### Requirement: VideoDeviceRepo
系统 SHALL 定义 `VideoDeviceRepo(BaseRepo[VideoDevice])`，提供视频设备数据访问。

- `model = VideoDevice`
- 特有方法 `by_node(node_id: int) -> list[VideoDevice]`：按所属节点查询

#### Scenario: 查询节点下的视频设备
- **WHEN** 调用 `video_repo.by_node(node_id=1)`
- **THEN** 返回该节点关联的所有 VideoDevice 记录

### Requirement: AudioDeviceRepo
系统 SHALL 定义 `AudioDeviceRepo(BaseRepo[AudioDevice])`，提供音频设备数据访问。

- `model = AudioDevice`
- 特有方法 `by_node(node_id: int) -> list[AudioDevice]`：按所属节点查询

#### Scenario: 查询节点下的音频设备
- **WHEN** 调用 `audio_repo.by_node(node_id=1)`
- **THEN** 返回该节点关联的所有 AudioDevice 记录

### Requirement: MonitorViewRepo
系统 SHALL 定义 `MonitorViewRepo(BaseRepo[MonitorView])`，提供监控视图数据访问。

- `model = MonitorView`
- 特有方法 `device_in_use(*, video_id=None, audio_id=None) -> bool`：检查指定视频或音频设备是否已被任何 View 引用
- 特有方法 `find_by_device(*, video_id=None, audio_id=None) -> list[MonitorView]`：查询使用指定设备的所有 View

#### Scenario: 创建 View 前检查视频设备占用
- **WHEN** 调用 `view_repo.device_in_use(video_id=5)`
- **THEN** 若已有 View 使用该设备返回 `True`，否则返回 `False`（前端据此显示告警）

#### Scenario: 删除 View 后检查是否释放
- **WHEN** 删除一个 View 后，调用 `view_repo.device_in_use(video_id=5)` 检查该视频设备
- **THEN** 若该视频设备不再被任何 View 引用，返回 `False`（表示已释放）

#### Scenario: 查询某设备被哪些 View 引用
- **WHEN** 调用 `view_repo.find_by_device(video_id=5)`
- **THEN** 返回所有引用该视频设备的 MonitorView 列表

### Requirement: ElectronicFenceRepo
系统 SHALL 定义 `ElectronicFenceRepo(BaseRepo[ElectronicFence])`，提供电子围栏数据访问。

- `model = ElectronicFence`

### Requirement: EntityTypeRepo
系统 SHALL 定义 `EntityTypeRepo(BaseRepo[EntityType])`，提供 YOLO 实体类型枚举数据访问。

- `model = EntityType`

### Requirement: ActionTypeRepo
系统 SHALL 定义 `ActionTypeRepo(BaseRepo[ActionType])`，提供 SlowFast 行为类型枚举数据访问。

- `model = ActionType`

### Requirement: SoundTypeRepo
系统 SHALL 定义 `SoundTypeRepo(BaseRepo[SoundType])`，提供 YAMNet 声音类型枚举数据访问。

- `model = SoundType`
