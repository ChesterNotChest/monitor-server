# Alert API (Delta)

## MODIFIED Requirements

### Requirement: Frontend receives alerts via WSS, falls back to REST

前端 SHALL 优先通过 WSS (`/ws/alerts`) 接收实时告警推送。
当 WSS 连接失败或断开时，前端 SHALL 降级为 REST 轮询 (`GET /api/v1/alerts`)，
轮询间隔为 30 秒。

#### Scenario: WSS primary, REST fallback

- **WHEN** WSS 连接正常
- **THEN** 前端告警列表通过 WSS 推送实时更新

#### Scenario: WSS disconnected, REST fallback active

- **WHEN** WSS 连接断开或无法建立
- **THEN** 前端自动切换到 30 秒 REST 轮询
- **AND** WSS 恢复连接后自动切回实时推送
