## 1. 基础设施 — BaseRepo（两人共同依赖）

- [ ] 1.1 创建 `src/repository/base.py` — `BaseRepo[T]` 泛型基类，实现 `get`/`all`/`create`/`delete`/`count`/`exists`/`paginate`

## 2. 组 A — 设备管理与 AI 枚举（人员 A）

- [ ] 2.1 创建 `src/repository/node_repo.py` — `NodeRepo`（继承 BaseRepo，新增 `by_token`）
- [ ] 2.2 创建 `src/repository/video_device_repo.py` — `VideoDeviceRepo`（继承 BaseRepo，新增 `by_node`）
- [ ] 2.3 创建 `src/repository/audio_device_repo.py` — `AudioDeviceRepo`（继承 BaseRepo，新增 `by_node`）
- [ ] 2.4 创建 `src/repository/monitor_view_repo.py` — `MonitorViewRepo`（继承 BaseRepo，新增 `device_in_use`、`find_by_device`）
- [ ] 2.5 创建 `src/repository/electronic_fence_repo.py` — `ElectronicFenceRepo`（继承 BaseRepo）
- [ ] 2.6 创建 `src/repository/entity_type_repo.py` — `EntityTypeRepo`（继承 BaseRepo）
- [ ] 2.7 创建 `src/repository/action_type_repo.py` — `ActionTypeRepo`（继承 BaseRepo）
- [ ] 2.8 创建 `src/repository/sound_type_repo.py` — `SoundTypeRepo`（继承 BaseRepo）

## 3. 组 B — 人员、告警与事件（人员 B，可与组 A 并行）

- [ ] 3.1 创建 `src/repository/named_person_repo.py` — `NamedPersonRepo`（继承 BaseRepo）
- [ ] 3.2 创建 `src/repository/alert_group_repo.py` — `AlertGroupRepo`（继承 BaseRepo，新增 `with_responses`）
- [ ] 3.3 创建 `src/repository/exception_def_repo.py` — `ExceptionDefRepo`（继承 BaseRepo，新增 `by_severity`、`by_group`、`with_details`）
- [ ] 3.4 创建 `src/repository/response_action_repo.py` — `ResponseActionRepo`（继承 BaseRepo，新增 `with_groups`）
- [ ] 3.5 创建 `src/repository/situation_event_repo.py` — `SituationEventRepo`（继承 BaseRepo，新增 `by_view`、`by_time_range`）

## 4. 集成验证

- [ ] 4.1 更新 `src/repository/__init__.py`，统一导出所有 Repository 类
- [ ] 4.2 验证所有 Repo 可正常导入并执行基本 CRUD
