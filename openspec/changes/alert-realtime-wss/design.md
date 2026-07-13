## Context

告警链路三处断裂：DB 无种子数据、Server→Web 无 WSS、SlowFast/YAMNet 事件缺陷。

## Goals / Non-Goals

**Goals:**
- AlertEngine 有规则可匹配（种子数据）
- 告警实时推送浏览器（WSS 替代轮询）
- SlowFast 和 YAMNet 事件正确发布

**Non-Goals:**
- 不改 AlertEngine 的匹配逻辑
- 不改 SituationEvent 的 DB 存储
- 不动 Server↔Node 的 WSS

## Decisions

### Decision 1: WSS 架构复用现有的 ConnectionRegistry 模式

**选择**：新增 `AlertConnectionRegistry`（类似 node 的 `ConnectionRegistry`），
在 `app.py` 中注册 `/ws/alerts` 端点。AlertEngine 创建告警后调用 registry 广播。

**理由**：与现有 Node WSS 架构一致，减少心智负担。

### Decision 2: 前端 WSS + REST 双模

**选择**：`AlertContext` 优先 WSS，断开时自动降级 REST 轮询。

**理由**：WSS 可能因网络问题断开，REST 保底确保告警不丢失。

### Decision 3: 种子数据最小集

**选择**：预置 person/car/dog/cat 四个实体类型 + 默认告警组 + "人员出现"异常规则。

**理由**：足够验证告警链路，不引入过多预设。

### Decision 4: SlowFast 使用 enqueue_and_publish

**选择**：`video_ai_processor.py` 中调用 `slowfast_runner.enqueue_and_publish()` 而非当前的 `enqueue() + collect_results()`。

**理由**：`enqueue_and_publish()` 已实现 ACTION 事件发布逻辑，只是调用方未使用。

## Risks / Trade-offs

- **[Risk]** WSS 连接数过多 → **Mitigation**：浏览器端单连接复用，每 tab 一个连接
- **[Risk]** 种子数据 ID 硬编码 → **Mitigation**：用 `get_or_create` 模式，幂等
