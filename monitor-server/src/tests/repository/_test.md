# Repository Tests

## Coverage
- **全部 13 个 Repository** 的冒烟测试（基础 CRUD + 特有方法）
- **每 Repo ≥1 个异常路径**（unique 约束、FK 约束、不存在记录、空值）
- **3 个集成测试场景**：View 生命周期、异常多对多关联、告警分组-响应关联

## Files
| File | Repo | Test Count |
|---|---|---|
| `test_node_repo.py` | NodeRepo | 9 |
| `test_video_device_repo.py` | VideoDeviceRepo | 7 |
| `test_audio_device_repo.py` | AudioDeviceRepo | 5 |
| `test_monitor_view_repo.py` | MonitorViewRepo | 9 |
| `test_electronic_fence_repo.py` | ElectronicFenceRepo | 3 |
| `test_entity_type_repo.py` | EntityTypeRepo | 3 |
| `test_action_type_repo.py` | ActionTypeRepo | 3 |
| `test_sound_type_repo.py` | SoundTypeRepo | 3 |
| `test_named_person_repo.py` | NamedPersonRepo | 5 |
| `test_alert_group_repo.py` | AlertGroupRepo | 5 |
| `test_exception_def_repo.py` | ExceptionDefRepo | 6 |
| `test_response_action_repo.py` | ResponseActionRepo | 4 |
| `test_situation_event_repo.py` | SituationEventRepo | 8 |
| `test_integration.py` | Multi-repo | 5 (4 test classes) |

## Run
```bash
pytest tests/repository/ -v
```
