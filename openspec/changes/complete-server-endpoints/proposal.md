## Why

前后端团队要以 Swagger (`http://localhost:8000/docs`) 为唯一标准进行并行开发对接。当前 server 端 63 个 REST 端点已存在，但 Swagger 文档质量参差不齐——部分 Pydantic Schema 缺少 Field description、部分端点缺少 response_model、错误响应不统一、RBAC 权限要求未在文档中体现。前端团队无法仅凭 Swagger 完成对接，被迫阅读后端源码，破坏了并行开发模式。

## What Changes

- **审查全部 Pydantic Schema**：确保每个 Field 有清晰的 description，让 Swagger 自动生成的文档对前端开发者友好
- **统一端点响应格式**：检查所有 router 是否声明了 `response_model`，消除返回裸 dict 的端点
- **标准化错误响应**：确保 400/404/409/422 等错误响应格式一致，并在 Swagger 中可见
- **RBAC 权限文档化**：在所有受保护端点的 docstring 中明确标注所需权限（如 `alert:handle`、`user:manage`）
- **Swagger Tag 整理**：确保 tags 命名一致、覆盖全面（当前 `/events` 和 `/events/stats` 使用了两个 router，但应归入同一 Tag 体系）
- **端点完整性验证**：逐端点对照 Swagger 验证实现无遗漏（无 stub、无 TODO、无 NotImplementedError）
- **WebSocket 补充文档**：WebSocket 不在 Swagger 覆盖范围内，需单独产出 WS 协议文档供前端参考

## Capabilities

### New Capabilities

- `swagger-documentation-audit`: 对全部 Pydantic Schema 和 API 端点进行 Swagger 文档质量审查，确保 Field description、response_model、Tag、docstring 完整且一致

### Modified Capabilities

- `schema-convention`: 补充 Field description 强制规范——所有面向 API 的 Pydantic Field 必须有 description
- `rbac-middleware`: 补充端点 docstring 中权限标注规范
- `alert-api`: 确保 AlertResponse 字段完整、分页响应格式统一
- `exception-crud-api`: 确保 ExceptionCreate/Response 与 error response 格式一致
- `fence-api`: 确保 FenceCreate/Response 字段完整且 description 清晰
- `user-management-api`: 确保 UserResponse 与 auth 中的 UserResponse 区分明确（两者字段不同是有意设计，需在 docs 中说明）
- `event-query-api`: 确保 events 和 events/stats 两个路由的 Tag 统一
- `view-management`: 确保 ViewCreateRequest 的 body vs query param 在 Swagger 中清晰可见

## Impact

- **Server 端代码**：`src/schema/http/*.py`（17 个文件）、`src/network/api/*.py`（所有 router）
- **WebSocket**：需新增 `openspec/specs/node-wss-connection/` 下的 WS 协议文档
- **无 API 破坏性变更**：Server 端已运行的端点行为不变，仅增强文档和补全缺失的元数据
- **前端受益**：前端团队可仅依据 Swagger + WS 文档完成全部对接工作，无需阅读后端源码
