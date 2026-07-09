## ADDED Requirements

### Requirement: 组 A 冒烟测试覆盖
系统 SHALL 为组 A 的 8 个 Repository 提供 pytest 格式的冒烟测试，覆盖基本 CRUD 和特有方法。

#### Scenario: NodeRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_node_repo.py`
- **THEN** 验证 `create`/`get`/`delete`/`by_token`/`paginate`/异常路径（不存在的 ID、重复 token）

#### Scenario: VideoDeviceRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_video_device_repo.py`
- **THEN** 验证 `create`/`get`/`by_node`/异常路径（FK 约束、重复 name）

#### Scenario: MonitorViewRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_monitor_view_repo.py`
- **THEN** 验证 `create`/`get`/`device_in_use`/`find_by_device`/异常路径（不存在的 video_id）

### Requirement: 组 B 冒烟测试覆盖
系统 SHALL 为组 B 的 5 个 Repository 提供 pytest 格式的冒烟测试。

#### Scenario: AlertGroupRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_alert_group_repo.py`
- **THEN** 验证 `create`/`get`/`with_responses`/异常路径

#### Scenario: ExceptionDefRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_exception_def_repo.py`
- **THEN** 验证 `create`/`get`/`by_severity`/`by_group`/`with_details`/异常路径（无效 severity 值、不存在的 group_id）

#### Scenario: SituationEventRepo 冒烟测试
- **WHEN** 运行 `tests/repository/test_situation_event_repo.py`
- **THEN** 验证 `create`/`get`/`by_view`/`by_time_range`/异常路径（不存在的 view_id 或 exception_id）

### Requirement: 异常路径覆盖
系统 SHALL 为每个 Repo 的冒烟测试包含至少 2 个异常路径场景。

#### Scenario: 唯一约束冲突
- **WHEN** 对具有 `unique=True` 的字段插入重复值
- **THEN** 测试用例验证抛出 `IntegrityError`

#### Scenario: 外键约束冲突
- **WHEN** 对具有外键的字段传入不存在的引用 ID
- **THEN** 测试用例验证抛出 `IntegrityError`

#### Scenario: 空值和默认值
- **WHEN** 创建记录时省略可空字段
- **THEN** 验证记录正常创建，可空字段为 None，有默认值的字段已填充
