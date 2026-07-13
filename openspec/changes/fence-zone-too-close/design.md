## Context

现有围栏检测为二元状态（ENTERED/EXITED），缺 TOO_CLOSE 警告区。停留判定用 `dwell_time`+`density` 而非直观的秒数。FENCE 事件键名 `result_id` 与 AlertEngine 期望的 `fence_event_ids` 不匹配，导致围栏告警从未触发。

## Goals

- 新增 TOO_CLOSE 状态，通过 `safe_distance` 像素缓冲区检测
- `entry_delay_seconds` 替换 `dwell_time`+`density`，直观的"停留X秒触发"
- 修复 FENCE→AlertEngine 事件键名

## Decisions

### Decision 1: 扩展多边形通过向量法外扩

**选择**：对 4 点围栏多边形的每条边向外平移 `safe_distance` 像素，取交点形成新四边形。

**理由**：几何精确，覆盖所有方向。对于不规则四边形，扩展后的形状仍是封闭多边形。

### Decision 2: entry_delay 用帧计数器

**选择**：每个 (fence, track) 维护 `_entry_frames` 计数器。Bbox 在围栏内时递增，离开时清零。当计数器 ≥ `entry_delay_seconds * fps` 时触发 ENTERED。

**理由**：简单可靠，不依赖密度计算。保留 `leave_frames` 用于退出判定（离开 N 帧后视为退出）。

### Decision 3: TOO_CLOSE 走独立 FenceEventResult 值

**选择**：`FenceEventResult` 新增 `TOO_CLOSE = 2`。`fence_event_types` 表新增 `(id=2, name="TOO_CLOSE")`。

**理由**：复用 ExceptionDef.fence_event_id 匹配机制，无需新建表。

### Decision 4: FENCE 事件统一键名

**选择**：fence_engine 发布时 payload 加 `fence_event_ids: [result_id]`。

**理由**：AlertEngine._cids 已使用 `fence_event_ids` 键名读取，最小改动。
