## Why

电子围栏目前仅有 ENTERED/EXITED 二元状态，无法表达"靠近但未进入"（TOO_CLOSE）的警告场景。此外：(1) 缺少安全距离缓冲区概念；(2) entry_delay 停留秒数不可配置；(3) FENCE 事件键名不匹配导致围栏告警从未触发。需补齐这三种告警状态并修复告警推送链路。

## What Changes

### 新区禁状态 TOO_CLOSE
- **ElectronicFence 模型**：新增 `safe_distance`（像素，缓冲区向外扩展距离，0=禁用）
- **FenceEventResult 枚举**：新增 `TOO_CLOSE = 2`
- **fence_engine.py**：检测 YOLO 框是否与扩展多边形交错但不接触原始多边形 → 发布 TOO_CLOSE 事件

### entry_delay 可配置停留秒数
- **ElectronicFence 模型**：新增 `entry_delay_seconds`（0=进入即触发，>0=连续停留X秒后触发 ENTERED）
- **fence_engine.py**：停留计时器，连续 N 帧在围栏内后触发 ENTERED

### FENCE 告警链路修复
- **fence_engine.py**：发布事件添加 `fence_event_ids` 键
- **AlertEngine**：修复 FENCE 事件读取键名
- **seed.py**：`fence_event_types` 表新增 TOO_CLOSE 行

### 前端
- **FenceEditor**：新增 `safe_distance`、`entry_delay_seconds` 输入

## Capabilities

### New Capabilities
- `fence-too-close`: 安全距离缓冲区，YOLO框靠近围栏但未进入时触发 TOO_CLOSE 告警
- `fence-entry-delay`: 可配置停留秒数，设为0立即触发，设为X秒则停留X秒后才触发 ENTERED

### Modified Capabilities
- `electronic-fence-model`: 模型新增 `safe_distance`、`entry_delay_seconds` 字段
- `fence-api`: CRUD 接口新增字段
- `ai-model-capability`: FENCE 事件发布键名修复，AlertEngine 能正确读取 fence_event_ids

## Impact

- `src/models/electronic_fence.py` — +`safe_distance`, +`entry_delay_seconds`
- `src/constants.py` — `FenceEventResult` +`TOO_CLOSE`
- `src/service/vision_module/vision_fence/fence_engine.py` — 扩展多边形 + TOO_CLOSE + entry_delay + 键名修复
- `src/service/alert_module/engine.py` — FENCE 键名修复
- `src/seed.py` — fence_event_types 种子数据
- `monitor-web/` — FenceEditor 新增输入
