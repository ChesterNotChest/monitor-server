# Schema Convention

**Purpose:** 定义 `src/schema/` 的目录结构与 HTTP / WSS 协议模型的分家规则。

## Requirements

### Requirement: Schema 层分家

`src/schema/` SHALL 按通信协议分为两个子包：`schema/http/`（REST 请求/响应模型）和 `schema/wss/`（WSS 命令协议模型）。两者的受众和文档化方式不同，SHALL 分开管理。

#### Scenario: 目录结构

- **WHEN** 查看 `src/schema/` 目录
- **THEN** 包含 `http/` 和 `wss/` 两个子包，各含 `__init__.py`

### Requirement: HTTP Schema — Swagger 自动渲染

`schema/http/` 中的 Pydantic 模型 SHALL 用作 FastAPI Router 的 `response_model` 和请求体参数。这些模型 SHALL 被 OpenAPI 自动渲染到 Swagger UI（`/docs`）——包括字段名、类型、必选/可选标记、示例值。

#### Scenario: REST 接口模型在 Swagger 中可见

- **WHEN** 前端开发者打开 `/docs`
- **THEN** 每个 REST 端点的 Request Body 和 Response Schema SHALL 自动展示字段结构，无需额外文档

#### Scenario: 新增 REST 接口

- **WHEN** 开发者在 `schema/http/view_schema.py` 中定义 `ViewCreateRequest` 和 `ViewResponse`
- **THEN** 在 Router 中引用后，Swagger UI 自动反映最新字段定义

### Requirement: WSS Schema — Pydantic 校验 + 手写文档

`schema/wss/` 中的 Pydantic 模型 SHALL 定义 Node 与 Server 之间的 WebSocket 消息格式。这些模型 SHALL 在代码中用于消息的序列化与反序列化校验（`model_validate()` / `model_dump()`），但 SHALL NOT 被 OpenAPI 自动文档化——WebSocket 消息级协议不在 OpenAPI 规范范围内。

#### Scenario: WSS 协议文档独立维护

- **WHEN** 需要查阅 Server ↔ Node 的 WSS 消息格式
- **THEN** 开发者查看 `src/schema/wss/node_commands.py` 中的 Pydantic 模型定义及配套 markdown 文档，而非 Swagger UI

#### Scenario: 新增加密/签名增强

- **WHEN** 后续引入公私钥签名后 WSS 消息格式需要变更
- **THEN** 仅修改 `schema/wss/` 下的模型，`schema/http/` 不受影响

### Requirement: 跨协议模型不混用

`schema/http/` 和 `schema/wss/` 中的模型 SHALL 各自独立，不互相引用。如果一个数据结构同时出现在 REST 和 WSS 中（如设备信息），SHALL 在两侧各自定义，保持解耦。

#### Scenario: 设备信息在两处出现

- **WHEN** REST API（`GET /nodes/{id}/videos`）和 WSS 响应（`get_devices_response`）都返回设备信息
- **THEN** `schema/http/` 和 `schema/wss/` 各定义一个设备模型，不共享引用——两边的字段需求可能随时间分化
