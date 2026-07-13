## Context

当前围栏检测为二元 ENTERED/EXITED 模型，进入判定依赖 `dwell_time` 时间窗口内的 density 密度计算。存在三个问题：

1. **无安全距离概念** — "靠近但未进入"无法表达，缺少预警层级
2. **density 判定不直观** — 用户不理解"10 秒窗口内 60% 帧在围栏内"意味着什么，调参困难，与帧率耦合
3. **FENCE 事件键名不匹配** — fence_engine 发布 `result_id`（单数），AlertEngine 期望 `fence_event_ids`（复数），围栏告警规则匹配路径存在 bug（当前因 AlertEngine 走全局快照未暴露，但隐患存在）

变更从 `yyh` 分支摘取围栏检测核心改进，保留 master 其余架构（全局快照 AlertEngine、RTMP 录制、WSS 推送）不变。

## Goals / Non-Goals

**Goals:**
- 新增 TOO_CLOSE 围栏事件状态，通过 `safe_distance` 像素缓冲区检测
- `entry_delay_seconds` 替换 density 密度计算，提供直观的"停留 N 秒触发"
- 修复 FENCE 事件键名 (`fence_event_ids`)
- 标注层和 ActiveSignals 完整适配 TOO_CLOSE

**Non-Goals:**
- 不改变 AlertEngine 架构（保持全局快照，不改成 EventBus 订阅模型）
- 不改变录制方案（保持 RTMP 拉流，不改成 pipe 写入）
- 不删除 WSS 告警推送
- 不修改 ExceptionDef 模型列
- 不修改 seed_alerts() 的完整告警种子
- 不在本次变更中清理 `dwell_time` / `density` 模型列（保留以兼容已有数据，仅废弃使用）

## Decisions

### Decision 1: 从 yyh Cherry-pick + 手写衔接

**选择**：从 `yyh` 分支摘取纯围栏检测文件，3 个衔接点（`_on_fence_event`、`get_active_signals`、`seed_fence_events`）手工编写。

**理由**：yyh 分支将告警引擎、录制引擎、WSS 等多个子系统一并重构（85 文件 / +1126 -2228 行），这些重构不在本次范围。直接 merge 会导致大量冲突且引入不需要的架构变更。Cherry-pick fence_engine.py 等核心文件 + 手写少量衔接代码是最高效的方式。

**备选方案**：`master → yyh` 全量合并后清理。被否决——清理工作量大于摘取工作量，且容易遗漏清理点。

### Decision 2: 扩展多边形通过向量法外扩

**选择**：对 4 点围栏多边形的每条边向外平移 `safe_distance` 像素取交点形成新四边形。三个辅助函数：
- `_normalize(v)` — 单位法向量
- `_line_intersection(a1, a2, b1, b2)` — 两线段交点
- `_expand_polygon(coords, dist)` — 主函数，遍历每条边计算外扩后的新顶点

结果缓存于 `_expanded: dict[int, list]`，仅在 `load_fences()` 时清空。

**理由**：几何精确，覆盖所有方向。对于不规则四边形，扩展后的形状仍是封闭多边形。与 yyh 实现一致，无需重新发明。

**备选方案**：简单地按比例放大（以质心为中心缩放）。被否决——对不规则形状会失真，缓冲区宽度不均匀。

### Decision 3: entry_delay 用时间戳而非帧计数

**选择**：每个 `(fence_id, track_id)` 维护 `_entry_start` 时间戳。Bbox 在围栏内时记录首次进入时间，离开时清除。当 `frame_timestamp - _entry_start >= entry_delay_seconds` 时触发 ENTERED。

**理由**：时间戳与帧率解耦，帧率波动不影响判定。保留 `leave_frames` 用于退出判定（离开 N 帧后视为退出）——退出是瞬时事件，帧计数合适。

**备选方案**：帧计数器。被否决——与帧率耦合，FPS 变化时行为不一致。

### Decision 4: TOO_CLOSE 走 FenceEventResult 枚举

**选择**：`FenceEventResult` 新增 `TOO_CLOSE = 2`，`fence_event_types` 种子表新增对应行。

**理由**：复用 ExceptionDef.fence_event_id 匹配机制——ExceptionDef 配置 `fence_event_id=2` 即可匹配 TOO_CLOSE，无需新建表或字段。

### Decision 5: 标注层 _on_fence_event 适配

**选择**：在回调中识别 `payload["fences"][*]["result"]` 值：
- `"ENTERED"` → `fence_labels[tid] = "Fence-{id}:IN"`
- `"TOO_CLOSE"` → `fence_labels[tid] = "Fence-{id}:TOO_CLOSE"`
- `entered=False` → 只清对应 track 的当前结果 label，不误删其他

**理由**：这是 yyh 缺失的逻辑——yyh 只改了检测引擎但没补标注层适配。必须手写，否则 TOO_CLOSE 标注会错乱。

### Decision 6: ActiveSignals 感知 TOO_CLOSE

**选择**：`get_active_signals()` 中从 `_fence_labels` 的值提取结果类型，而非硬编码 `{FenceEventResult.ENTERED}`：
- label 含 `":IN"` → `fence_result_ids` 加 `ENTERED (1)`
- label 含 `":TOO_CLOSE"` → `fence_result_ids` 加 `TOO_CLOSE (2)`

**理由**：这是另一个 yyh 缺失点。不修的话 ExceptionDef 配了 `fence_event_id=2` 的规则永远不会匹配，TOO_CLOSE 告警链路断裂。

### Decision 7: seed_fence_events 精确幂等检查

**选择**：检查 `FenceEventType` 表是否同时存在 `id=1` 和 `id=2`，而非检查表是否非空：
```python
existing_ids = {r.id for r in db.query(FenceEventType).all()}
if 1 in existing_ids and 2 in existing_ids:
    return
if 1 not in existing_ids:
    db.add(FenceEventType(id=1, name="ENTERED"))
if 2 not in existing_ids:
    db.add(FenceEventType(id=2, name="TOO_CLOSE"))
```

**理由**：`seed_alerts()` 先运行时已经插入了 `id=1 (ENTERED)` 到 FenceEventType 表。若新函数仅检查表非空，TOO_CLOSE 永远不会被插入。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| detect 循环重写引入计时器边界 bug（TOO_CLOSE ↔ ENTERED 切换时 `_entry_start` 被错误清空） | E2E 测试覆盖 3 场景：safe_distance=50 靠近、entry_delay=3s 停留触发、entry_delay=0 立即触发 |
| `leave_frames` 断连时 TOO_CLOSE 与 ENTERED 的退出逻辑混用（共享 `_leave_counts[key]`） | 两个状态写法一致，共享计数器是设计意图——无论从哪个状态离开，都是"连续 N 帧不在区域内即退出" |
| 多边形扩展对凹四边形可能产生自交形状 | `_expand_polygon` 假设凸四边形。如果用户绘制凹围栏，扩展结果可能不可用。短期内前端限制凸四边形输入，长期可用 Shapely buffer 替换 |
| `dwell_time`/`density` 列残留在 DB 中成为死字段 | 本次保留列不动，仅废弃使用。后续清理属于独立变更 |
