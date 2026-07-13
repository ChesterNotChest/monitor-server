## 1. 模型 + Schema

- [ ] 1.1 `electronic_fence.py` — 新增 `safe_distance` 和 `entry_delay_seconds` 列
- [ ] 1.2 `fence_schema.py` — FenceCreate/Response 新增对应字段

## 2. TOO_CLOSE 枚举 + 种子

- [ ] 2.1 `constants.py` — `FenceEventResult` 新增 `TOO_CLOSE = 2`
- [ ] 2.2 `seed.py` — `fence_event_types` 表新增 TOO_CLOSE 行

## 3. Fence Engine 核心逻辑

- [ ] 3.1 `fence_engine.py` — 扩展多边形计算（向量外扩 `safe_distance` 像素）
- [ ] 3.2 `fence_engine.py` — TOO_CLOSE 检测 + 发布事件
- [ ] 3.3 `fence_engine.py` — `entry_delay_seconds` 帧计数器替换密度逻辑
- [ ] 3.4 `fence_engine.py` — payload 添加 `fence_event_ids` 键

## 4. AlertEngine 键名修复

- [ ] 4.1 `engine.py` — FENCE 事件 `_cids` 键名已为 `fence_event_ids`，确认 fence_engine 发布对齐

## 5. 前端

- [ ] 5.1 `FenceEditor.tsx` — 表单新增 `safe_distance` 和 `entry_delay_seconds` 输入
- [ ] 5.2 `types.ts` — FenceCreate/Response 新增字段

## 6. 端到端验证

- [ ] 6.1 创建围栏设置 `safe_distance=50` → 人物靠近 → 前端收到 TOO_CLOSE 告警
- [ ] 6.2 设置 `entry_delay_seconds=3` → 人物进入 3 秒后才告警
- [ ] 6.3 设置 `entry_delay_seconds=0` → 人物进入立即告警
