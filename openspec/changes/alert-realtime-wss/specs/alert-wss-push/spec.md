# Alert WSS Push

## Purpose

Server 通过 WebSocket 向浏览器实时推送告警事件，替代 30 秒 REST 轮询。

## ADDED Requirements

### Requirement: Server exposes frontend-facing WSS endpoint

Server SHALL 在 `/ws/alerts` 路径注册 WebSocket 端点，接受浏览器连接。
连接 SHALL 通过 JWT token 进行身份验证。

#### Scenario: Browser connects to alert WSS

- **WHEN** 浏览器携带有效 JWT token 连接 `ws://server/ws/alerts`
- **THEN** Server 接受连接并保持 WebSocket 会话

#### Scenario: Invalid token rejected

- **WHEN** 浏览器携带无效或过期 token 连接
- **THEN** Server 关闭连接并返回 401

### Requirement: AlertEngine broadcasts on WSS

AlertEngine 创建 SituationEvent 后 SHALL 通过 WSS 广播该告警到所有已连接的浏览器。

#### Scenario: Alert pushed in real-time

- **WHEN** AlertEngine 匹配到一条 ExceptionDef 规则并创建 SituationEvent
- **THEN** 所有已连接的浏览器在 1 秒内收到该告警的 JSON 消息

### Requirement: WSS message format

WSS 推送消息 SHALL 使用与 `GET /api/v1/alerts` 相同的 `AlertResponse` 格式。

#### Scenario: WSS alert format

- **WHEN** Server 通过 WSS 推送告警
- **THEN** 消息 JSON 结构与 REST API `AlertListResponse` 中的单个告警条目一致
