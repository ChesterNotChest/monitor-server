## ADDED Requirements

### Requirement: View 生命周期集成测试
系统 SHALL 在 `tests/repository/test_integration.py` 中提供多 Repo 协作的集成测试，覆盖 View 从创建到删除的完整生命周期及设备占用/释放逻辑。

#### Scenario: 创建 View 后设备被占用
- **WHEN** 创建 Node → VideoDevice → AudioDevice → MonitorView（关联这些设备）
- **THEN** `device_in_use(video_id=...)` 和 `device_in_use(audio_id=...)` 均返回 True

#### Scenario: 删除 View 后设备释放
- **WHEN** 删除 MonitorView
- **THEN** `device_in_use(video_id=...)` 和 `device_in_use(audio_id=...)` 均返回 False

#### Scenario: 仅视频的 View（无音频）
- **WHEN** 创建 MonitorView 仅指定 video_id（audio_id=None）
- **THEN** View 创建成功，`device_in_use(video_id=...)` 为 True，`device_in_use(audio_id=...)` 为 False

### Requirement: 异常定义关联集成测试
系统 SHALL 提供 ExceptionDef 与其多对多关联表（entities/actions/sounds）的集成测试。

#### Scenario: 完整异常定义创建
- **WHEN** 创建 AlertGroup → 创建 EntityType/ActionType/SoundType → 创建 ExceptionDef 并关联到分组
- **THEN** `with_details()` 返回的异常包含预加载的关联数据
