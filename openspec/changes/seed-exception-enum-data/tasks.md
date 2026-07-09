## 1. 种子数据脚本

- [ ] 1.1 新建 `src/seed_data.py`：模块入口，调用各 seed 函数
- [ ] 1.2 实现 `seed_entity_types(db)` — 通过 EntityTypeRepo 幂等插入 15 条 YOLO 实体
- [ ] 1.3 实现 `seed_action_types(db)` — 通过 ActionTypeRepo 幂等插入 15 条 SlowFast 行为
- [ ] 1.4 实现 `seed_sound_types(db)` — 通过 SoundTypeRepo 幂等插入 15 条 YAMNet 声音
- [ ] 1.5 实现 `seed_response_actions(db)` — 通过 ResponseActionRepo 幂等插入 5 条响应动作
- [ ] 1.6 实现 `seed_alert_groups(db)` — 通过 AlertGroupRepo 幂等插入 4 条告警分组 + 绑定对应的 ResponseAction
- [ ] 1.7 实现 `seed_exceptions(db)` — 通过 ExceptionDefRepo + binding 模块幂等插入 8 条规则 + M2M 绑定
- [ ] 1.8 幂等逻辑：每条先查询是否存在（按 name），存在则更新，不存在则创建

## 2. 验证

- [ ] 2.1 删除旧数据库，运行 `python -m src.seed_data`，确认所有枚举和规则正确入库
- [ ] 2.2 再次运行种子脚本，确认幂等（无异常、无重复）
- [ ] 2.3 启动应用，通过 `/docs` 验证所有枚举端点返回种子数据
