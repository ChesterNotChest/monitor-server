## 1. CI 基础设施

- [x] 1.1 创建 `tests/conftest.py` — 全局 fixtures（`engine`、`db`），SQLite PRAGMA FK 开启
- [x] 1.2 创建 `pytest.ini` — 配置 `testpaths = tests`

## 2. 组 A 冒烟测试（repository 层）

- [x] 2.1 创建 `tests/repository/test_node_repo.py` — NodeRepo CRUD + `by_token` + 异常路径
- [x] 2.2 创建 `tests/repository/test_video_device_repo.py` — VideoDeviceRepo CRUD + `by_node` + 异常路径
- [x] 2.3 创建 `tests/repository/test_audio_device_repo.py` — AudioDeviceRepo CRUD + `by_node` + 异常路径
- [x] 2.4 创建 `tests/repository/test_monitor_view_repo.py` — MonitorViewRepo CRUD + `device_in_use` + `find_by_device` + 异常路径
- [x] 2.5 创建 `tests/repository/test_electronic_fence_repo.py` — ElectronicFenceRepo CRUD + 异常路径
- [x] 2.6 创建 `tests/repository/test_entity_type_repo.py` — EntityTypeRepo CRUD + 异常路径
- [x] 2.7 创建 `tests/repository/test_action_type_repo.py` — ActionTypeRepo CRUD + 异常路径
- [x] 2.8 创建 `tests/repository/test_sound_type_repo.py` — SoundTypeRepo CRUD + 异常路径

## 3. 组 B 冒烟测试（repository 层）

- [x] 3.1 创建 `tests/repository/test_named_person_repo.py` — NamedPersonRepo CRUD + 异常路径
- [x] 3.2 创建 `tests/repository/test_alert_group_repo.py` — AlertGroupRepo CRUD + `with_responses` + 异常路径
- [x] 3.3 创建 `tests/repository/test_exception_def_repo.py` — ExceptionDefRepo CRUD + `by_severity` + `by_group` + `with_details` + 异常路径
- [x] 3.4 创建 `tests/repository/test_response_action_repo.py` — ResponseActionRepo CRUD + `with_groups` + 异常路径
- [x] 3.5 创建 `tests/repository/test_situation_event_repo.py` — SituationEventRepo CRUD + `by_view` + `by_time_range` + 异常路径

## 4. 集成测试

- [x] 4.1 创建 `tests/repository/test_integration.py` — View 生命周期集成测试（Node→Device→View→删除→设备释放）+ 异常定义多对多关联测试

## 5. E2E 骨架

- [x] 5.1 创建 `tests/e2e/_test.md` — E2E 测试说明文档
- [x] 5.2 创建 `tests/e2e/conftest.py` — E2E 专用 fixtures（预留）

## 6. 说明文档

- [x] 6.1 创建 `tests/repository/_test.md` — repository 测试覆盖说明
- [x] 6.2 创建 `tests/service/_test.md` — service 测试预留说明
- [x] 6.3 创建 `tests/api/_test.md` — API 测试预留说明
- [x] 6.4 删除 `src/repository/_smoke_test.py` — 旧的临时冒烟脚本

## 7. 验证

- [x] 7.1 运行 `pytest tests/ -v` 确认全部测试通过

## 8. Test quality cleanup

- [x] 8.1 Specify that pytest-discovered placeholder tests with only `pass` should not be kept.
- [x] 8.2 Remove obsolete placeholder files once concrete runtime and WSS integration tests cover the behavior.
- [x] 8.3 Run the server test suite after cleanup.
