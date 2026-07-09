# Part C — 音频 + 告警

> **负责人**: ___
> **依赖**: Part A（EventBus 接口）
> **并行策略**: YAMNet 完全独立，告警引擎依赖 EventBus 事件类型定义

## 11. YAMNet 音频分类

- [ ] 11.1 创建 `src/service/ai_module/yamnet_runner.py`：`YamnetRunner` 类
- [ ] 11.2 FFmpeg 子进程拉流：`ffmpeg -i rtmp://srs/live/audio_{id} -f f32le -ac 1 -ar 16000 pipe:1`
- [ ] 11.3 加载 YAMNet 模型（tensorflow-hub，首次自动缓存）
- [ ] 11.4 `run()` → 每 0.96s 累积样本量 → YAMNet 推理 → 输出 `(521,)` scores
- [ ] 11.5 AudioSet class_id → SoundType 15 类映射（定义在 `ai-model-capability` spec）
- [ ] 11.6 `YAMNET_THRESHOLD`（默认 0.5），概率 > 阈值 → SoundType 事件
- [ ] 11.7 Publish SoundType 到 EventBus topic `SOUND`
- [ ] 11.8 状态机：IDLE → ACTIVE → ERROR，断流重连（指数退避 1s→60s）

## 12. 告警引擎

- [ ] 12.1 创建 `src/service/ai_module/alert_engine.py`：`AlertEngine` 类
- [ ] 12.2 订阅 EventBus 全部 5 个 event type
- [ ] 12.3 内存活跃事件池：`{event_type: [{payload, expires_at}, ...]}`，事件 TTL = `ALERT_EVENT_TTL`（默认 5s）
- [ ] 12.4 每 `ALERT_CHECK_INTERVAL`（默认 5s）触发一次检查：
  - 清理过期事件
  - 收集当前活跃的 `{entity_type_ids, action_type_ids, sound_type_ids, face_result_ids, fence_event_ids}`
  - 加载 View 关联的所有 `ExceptionDef`
  - 逐条匹配：全部关联条件都满足 → 触发
- [ ] 12.5 匹配逻辑（AND）：
  ```
  def.entities ⊆ active_entities
  AND def.actions ⊆ active_actions
  AND def.sounds ⊆ active_sounds
  AND (def.face_result_id IS NULL OR def.face_result_id ∈ active_face_results)
  AND (def.fence_event_id IS NULL OR def.fence_event_id ∈ active_fence_events)
  → TRIGGER
  ```
- [ ] 12.6 去重：`(view_id, exception_def_id, timestamp // ALERT_CHECK_INTERVAL)` → 不重复
- [ ] 12.7 触发：创建 `SituationEvent(view_id, exception_id)` + 查 AlertGroup → 写 DB
- [ ] 12.8 去重保持 `ALERT_COOLDOWN` 秒（默认 30s）：同一规则触发后冷却期内不再触发

## 13. FenceEventType CRUD API（枚举管理）

- [ ] 13.1 新增 `GET /api/v1/detection/fence-event-types` — 列表
- [ ] 13.2 新增 `POST /api/v1/detection/fence-event-types` — 创建
- [ ] 13.3 新增 `PUT /api/v1/detection/fence-event-types/{item_id}` — 更新
- [ ] 13.4 新增 `DELETE /api/v1/detection/fence-event-types/{item_id}` — 删除
- [ ] 13.5 与现有 `entity-types`、`action-types`、`sound-types` API 保持一致路由风格

## 14. App 集成

- [ ] 14.1 创建 `src/service/ai_module/__init__.py`：导出 `AIPipeline` 门面类
- [ ] 14.2 `AIPipeline` 门面：`start(view_id, video_id, audio_id)` → 启动全部模块 → 主循环；`stop()` → 逐一停止
- [ ] 14.3 注册到 Server lifespan：View 创建回调 → `AIPipeline.start()`；View 删除回调 → `AIPipeline.stop()`
- [ ] 14.4 崩溃隔离：单个模块异常不中断主循环，异常模块标记 ERROR 后跳过

## 15. 测试

### 15.1 YAMNet
- [ ] 15.1.1 给定测试音频（含枪声片段）→ GUNSHOT 事件
- [ ] 15.1.2 无声片段 → SILENCE 事件
- [ ] 15.1.3 FFmpeg 拉流 mock → 断流重连

### 15.2 告警引擎
- [ ] 15.2.1 ExceptionDef 全部条件满足 → 触发
- [ ] 15.2.2 部分条件 → 不触发
- [ ] 15.2.3 同窗口去重
- [ ] 15.2.4 SituationEvent + AlertGroup 写入 DB
- [ ] 15.2.5 冷却期内不重复触发
- [ ] 15.2.6 混合条件（实体 + 围栏）、（声音 + 人脸）AND 逻辑正确

### 15.3 FenceEventType CRUD
- [ ] 15.3.1 POST fence-event-types → 201
- [ ] 15.3.2 GET fence-event-types → 列表含 ENTERED
- [ ] 15.3.3 PUT fence-event-types/{id} → 200
- [ ] 15.3.4 DELETE fence-event-types/{id} → 204
