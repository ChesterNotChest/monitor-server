## 1. 告警种子数据

- [ ] 1.1 `seed.py` — 添加 EntityType 种子（person、car、dog、cat）
- [ ] 1.2 `seed.py` — 添加默认 AlertGroup
- [ ] 1.3 `seed.py` — 添加 ExceptionDef（"人员出现" 关联 person + 默认告警组）

## 2. Server→Web WSS 实时推送

- [ ] 2.1 新建 `src/network/wss/alert_handler.py` — Alert WSS 端点，JWT 认证 + 连接管理
- [ ] 2.2 `app.py` — 注册 `/ws/alerts` WebSocket 路由
- [ ] 2.3 `alert_module/engine.py` — AlertEngine 创建 SituationEvent 后调用 WSS 广播
- [ ] 2.4 `alert_task.py` — 告警查询返回格式与 WSS 推送格式一致

## 3. 前端 WSS 集成

- [ ] 3.1 `AlertContext.tsx` — 新建 WSS 连接，接收实时告警推送
- [ ] 3.2 `AlertContext.tsx` — WSS 断开时自动降级 REST 轮询
- [ ] 3.3 `client.ts` — 保留 fetchAlerts 作为降级方案

## 4. SlowFast + YAMNet 事件修复

- [ ] 4.1 `video_ai_processor.py` — SlowFast 改用 `enqueue_and_publish()` 发布 ACTION 事件
- [ ] 4.2 `audio_yamnet.py` — 修复键名 `sound_type` → `sound_type_ids`

## 5. 端到端验证

- [ ] 5.1 清 DB 重启 → 确认种子数据自动创建
- [ ] 5.2 创建 View → 人员进入摄像头 → 浏览器实时收到告警
- [ ] 5.3 断开 WSS → 确认自动降级到 REST 轮询
