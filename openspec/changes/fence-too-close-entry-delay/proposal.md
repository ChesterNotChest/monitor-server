## Why

电子围栏目前仅有 ENTERED/EXITED 二元状态，无法表达"靠近但未进入"（TOO_CLOSE）的警告场景。进入判定使用 density 密度计算（dwell_time 窗口内帧比例≥阈值），概念不直观、与帧率耦合、用户难以理解。此外，FENCE 事件 payload 键名 `result_id` 与 AlertEngine 期望的 `fence_event_ids` 不匹配——虽然当前 AlertEngine 走全局快照不读 EventBus，但 bug 本身客观存在。

从 `yyh` 分支摘取围栏核心改进，丢弃不相关的架构重构（EventBus 订阅、录制 pipe、WSS 删除等）。

## What Changes

- **ElectronicFence 模型**：新增 `safe_distance`（像素，安全距离缓冲区，0=禁用 TOO_CLOSE）、`entry_delay_seconds`（秒，进入后停留 N 秒触发 ENTERED，0=立即触发）
- **FenceEventResult 枚举**：新增 `TOO_CLOSE = 2`
- **围栏检测引擎**：密度窗口（dwell_time + density）替换为时间机制（entry_delay_seconds + 帧计数）；新增 TOO_CLOSE 状态检测（bbox 在扩展多边形内但不在原始多边形内）；新增 `get_track_states()` 方法供标注层消费
- **多边形扩展**：向量法外扩——每条边向外平移 safe_distance 像素取交点，几何精确
- **FENCE 事件键名修复**：payload 增加 `fence_event_ids` 键
- **标注层适配**：`_on_fence_event` 识别 TOO_CLOSE 标签；`get_active_signals` 感知 TOO_CLOSE → `{2}` 以便 ExceptionDef 规则匹配
- **种子数据**：`seed_fence_events` 精确检查并插入 `FenceEventType(id=2, name="TOO_CLOSE")`
- **绘制**：扩展多边形以红色细线叠加显示

## Capabilities

### New Capabilities
- `fence-too-close`: YOLO 检测框靠近围栏安全距离缓冲区但未进入时触发 TOO_CLOSE 事件，含 EventBus 发布、标注标签更新、ActiveSignals 提取、告警规则匹配的完整链路
- `fence-entry-delay`: 可配置停留秒数，设为 0 立即触发 ENTERED，设为 N 秒则连续停留 N 秒后才触发

### Modified Capabilities
- `electronic-fence-model`: 新增 `safe_distance`、`entry_delay_seconds` 列
- `fence-api`: CRUD 接口新增 `safe_distance`、`entry_delay_seconds` 字段
- `ai-model-capability`: 围栏检测引擎以 TOO_CLOSE 状态 + entry_delay 计时器替代 density 密度计算；EventBus FENCE 事件 payload 增加 `fence_event_ids` 键

## Impact

- `src/models/electronic_fence.py` — +`safe_distance`, +`entry_delay_seconds`
- `src/constants.py` — `FenceEventResult` +`TOO_CLOSE = 2`
- `src/schema/http/fence_schema.py` — FenceCreate/Response +2 字段
- `src/service/vision_module/vision_fence/fence_engine.py` — 密度→延时 + TOO_CLOSE + 多边形扩展 + 键名修复 + get_track_states
- `src/service/fence_task.py` — 参数透传 +2
- `src/network/api/fence_router.py` — API 透传 +2
- `src/seed.py` — +`seed_fence_events()` 精确插入 id=2 TOO_CLOSE
- `src/service/vision_module/vision_annotation.py` — `_on_fence_event` 适配 TOO_CLOSE、`get_active_signals` 适配、绘制扩展多边形
- `src/service/vision_module/vision_pipeline.py` — FrameContext +`fence_expanded_polygons`
- DB migration — ElectronicFence 表 +2 列，FenceEventType 表 +TOO_CLOSE 行
