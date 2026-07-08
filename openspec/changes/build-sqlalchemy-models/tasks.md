## 1. 枚举常量定义

- [ ] 1.1 在 `src/constants.py` 中新增 YOLO 实体类型枚举、SlowFast 行为类型枚举、YAMNet 声音类型枚举、异常严重级别枚举、响应动作类型枚举

## 2. 计算机节点与设备模型

- [ ] 2.1 创建 `src/models/node.py` — Node 模型（id, token）
- [ ] 2.2 创建 `src/models/video_device.py` — VideoDevice 模型（id, name, node_id → nodes.id）
- [ ] 2.3 创建 `src/models/audio_device.py` — AudioDevice 模型（id, name, node_id → nodes.id）

## 3. 监控视图模型

- [ ] 3.1 创建 `src/models/monitor_view.py` — MonitorView 模型（id, video_id → video_devices.id, audio_id → audio_devices.id, cache_path）

## 4. 电子围栏模型

- [ ] 4.1 创建 `src/models/electronic_fence.py` — ElectronicFence 模型（id, coords）

## 5. AI 检测枚举模型

- [ ] 5.1 创建 `src/models/entity_type.py` — EntityType 模型（id, name）
- [ ] 5.2 创建 `src/models/action_type.py` — ActionType 模型（id, name）
- [ ] 5.3 创建 `src/models/sound_type.py` — SoundType 模型（id, name）

## 6. 命名人物模型

- [ ] 6.1 创建 `src/models/named_person.py` — NamedPerson 模型（id, avatar_path, feat_json_id）

## 7. 告警分组模型

- [ ] 7.1 创建 `src/models/alert_group.py` — AlertGroup 模型（id, name）

## 8. 异常枚举与关联模型

- [ ] 8.1 创建 `src/models/exception.py` — Exception 模型（id, severity, group_id → alert_groups.id）+ 三张多对多关联表（exception_entities, exception_actions, exception_sounds）

## 9. 响应动作模型

- [ ] 9.1 创建 `src/models/response_action.py` — ResponseAction 模型（id, name）+ alert_group_responses 关联表（group_id, response_id）

## 10. 事件模型

- [ ] 10.1 创建 `src/models/situation_event.py` — SituationEvent 模型（id, view_id → monitor_views.id, exception_id → exceptions.id, timestamp）

## 11. 模型注册

- [ ] 11.1 更新 `src/models/__init__.py`，导入所有模型以便 `Base.metadata.create_all` 自动建表
