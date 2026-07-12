## Why

AI 推理管线已正常运行，但告警链路有三处断裂：(1) DB 无种子数据→AlertEngine 无规则可匹配→零告警产生；(2) Server→Web 无实时推送通道→前端只能 30 秒轮询；(3) SlowFast 和 YAMNet 事件发布有缺陷→行为和音频告警永远无法触发。

## What Changes

- **seed.py**：新增 EntityType、ActionType、SoundType、AlertGroup、ExceptionDef 预置种子数据，AlertEngine 有规则可匹配
- **新增 Server→Web WSS 端点**：AlertEngine 创建 SituationEvent 后通过新 WSS 广播到已连接浏览器
- **AlertContext.tsx**：前端从 REST 轮询改为 WSS 连接，实现实时推送
- **SlowFast 事件修复**：`video_ai_processor.py` 改用 `enqueue_and_publish()` 发布 ACTION 事件
- **YAMNet 键名修复**：`audio_yamnet.py` 发布 `sound_type_ids` 而非 `sound_type`，对齐 AlertEngine

## Capabilities

### New Capabilities
- `alert-seed-data`: 预置告警规则种子数据（实体类型、行为类型、声音类型、告警分组、异常定义）
- `alert-wss-push`: Server→Web WSS 实时告警推送通道，替代 30 秒轮询

### Modified Capabilities
- `alert-api`: 前端告警获取方式从 REST 轮询改为 WSS 推送
- `ai-model-capability`: SlowFast 行为识别结果需发布 ACTION 事件到 EventBus；YAMNet 音频识别结果键名对齐

## Impact

- `src/seed.py` — 新增告警种子数据
- `src/network/wss/` — 新增前端告警 WSS 端点和处理程序
- `src/service/alert_module/engine.py` — WSS 广播集成
- `src/service/vision_module/video_ai_processor.py` — SlowFast publish
- `src/service/audio_module/audio_yamnet.py` — 键名修复
- `src/app.py` — 注册新 WSS 路由
- `monitor-web/src/context/AlertContext.tsx` — WSS 替代轮询
- `monitor-web/src/api/client.ts` — 保留 REST 作为降级
