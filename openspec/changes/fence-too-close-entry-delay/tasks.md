## 1. 模型 + 枚举 + Schema（Cherry-pick）

- [x] 1.1 `src/models/electronic_fence.py` — 新增 `safe_distance`、`entry_delay_seconds` 列（从 yyh cherry-pick）
- [x] 1.2 `src/constants.py` — `FenceEventResult` 新增 `TOO_CLOSE = 2`（从 yyh cherry-pick）
- [x] 1.3 `src/schema/http/fence_schema.py` — `FenceCreate`/`FenceResponse` 新增 `safe_distance`、`entry_delay_seconds`（从 yyh cherry-pick）

## 2. 围栏检测引擎（Cherry-pick fence_engine.py 整体）

- [x] 2.1 `src/service/vision_module/vision_fence/fence_engine.py` — 从 yyh cherry-pick 整体，包含：密度→延时替换、TOO_CLOSE 三态状态机、`_expand_polygon` 向量扩展、`_get_expanded` 缓存、`expanded_polygons` 属性、`get_track_states()` 方法、`fence_event_ids` 键名修复、75 帧 debug 日志、`_cleanup_stale` 适配 TOO_CLOSE

## 3. 标注层适配（手工修改）

- [x] 3.1 `src/service/vision_module/vision_annotation.py` — `_on_fence_event()` 适配：识别 `result="TOO_CLOSE"`，设置 label 为 `"Fence-{id}:TOO_CLOSE"`；`entered=False` 时精确清除对应 track 的 label
- [x] 3.2 `src/service/vision_module/vision_annotation.py` — `get_active_signals()` 适配：从 `_fence_labels` 值解析 `:TOO_CLOSE` → `fence_result_ids` 含 `{2}`，`:IN` → 含 `{1}`
- [x] 3.3 `src/service/vision_module/vision_annotation.py` — `draw_fence_polygons()` 支持 `expanded` 参数（从 yyh cherry-pick）；`draw_part_b_overlay()` 支持 `fence_expanded_polygons` 参数（从 yyh cherry-pick）

## 4. Pipeline + Service + Router（Cherry-pick + 透传）

- [x] 4.1 `src/service/vision_module/vision_pipeline.py` — `FrameContext` 新增 `fence_expanded_polygons` 字段；绘制调用传入扩展多边形
- [x] 4.2 `src/service/fence_task.py` — `create_fence()`/`update_fence()` 新增 `safe_distance`、`entry_delay_seconds` 参数（从 yyh cherry-pick）
- [x] 4.3 `src/network/api/fence_router.py` — 创建/更新端点透传新字段（从 yyh cherry-pick）

## 5. 种子数据（手工修改）

- [x] 5.1 `src/seed.py` — 新增 `seed_fence_events()` 函数，精确幂等：检查 `id=1` 和 `id=2` 是否均已存在，缺哪个插哪个；`seed_alerts()` 的 `_FENCE_EVENT_NAMES` 同步加入 `too_close`
- [x] 5.2 `src/app.py` — 启动时调用 `seed_fence_events()`

## 6. 数据库迁移

- [x] 6.1 创建 migration SQL：`ElectronicFence` +2 列（`safe_distance`、`entry_delay_seconds`，默认 0）
- [x] 6.2 migration SQL 包含 `INSERT OR IGNORE INTO fence_event_types (id=2, name="TOO_CLOSE")`（幂等）

## 7. 端到端验证

- [ ] 7.1 创建围栏设置 `safe_distance=50` → 人物靠近扩展区 → 标注层显示 `Fence-{id}:TOO_CLOSE`、前端（如已适配）收到 TOO_CLOSE 告警
- [ ] 7.2 设置 `entry_delay_seconds=3` → 人物进入围栏 → 3 秒后才触发 ENTERED，3 秒内离开不触发
- [ ] 7.3 设置 `entry_delay_seconds=0` → 人物进入围栏 → 立即触发 ENTERED
- [ ] 7.4 `FenceEventType` 表同时存在 id=1 (ENTERED) 和 id=2 (TOO_CLOSE)，seed 幂等重跑不报错
