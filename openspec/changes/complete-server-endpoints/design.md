## Context

当前 server 端有 17 个 router 文件、63 个 REST 端点、2 个 WebSocket 端点。所有端点均已实现并可运行，但 Swagger 文档存在以下问题：

- **Field description 缺失**：大量 Pydantic Field 只定义了类型和校验，无 description。Swagger 将显示空白的字段说明。
- **response_model 缺失**：部分 router 函数未声明 `response_model`，Swagger 无法推断响应结构，显示为 `{}` 或无 schema。
- **裸 dict 返回**：部分端点返回 `{"ok": true}` 或 `{"views": [...]}`，Swagger 将其标记为 `object` 而非具体类型。
- **错误响应不可见**：FastAPI 的 `HTTPException` 虽然会触发标准错误响应，但 Swagger 默认不展示可能抛出的错误状态码和 body。
- **RBAC 权限隐式**：`Depends(require_permission("alert:handle"))` 在 Swagger 中以锁图标显示，但无说明具体权限标识符是什么。
- **WebSocket 无 Swagger 覆盖**：OpenAPI 3.x 不支持 WebSocket，前端开发者无法从 `/docs` 了解 WS 协议。

## Goals / Non-Goals

**Goals:**
- 使 Swagger (`/docs`) 成为前端开发者**唯一需要参考的 REST API 文档**——无需阅读后端源码
- 统一 Field description 规范：所有 Pydantic Field 有 description
- 统一错误响应格式：所有端点在其 docstring 或 response 装饰器中声明可能的错误状态码
- RBAC 权限字符串对所有受保护端点可见
- WebSocket 协议有独立文档（Markdown），与 Swagger 互补

**Non-Goals:**
- 不修改 API 端点的行为逻辑（不重构业务逻辑）
- 不新增或删除 REST 端点
- 不修改数据库 schema
- 不处理前端代码——前端类型对齐是另一个 change
- 不引入 OpenAPI 扩展工具（如 drf-spectacular）——保持 FastAPI 原生方式

## Decisions

### D1：Field description 使用中文还是英文？

**决策**：使用中文。

**理由**：项目成员和前端团队均为中文母语者。现有代码中已有大量中文 docstring（如 `"""POST /api/v1/views — 创建监控视图，启动 FFmpeg 合流。"""`）。保持一致性。

### D2：RBAC 权限标注方式

**决策**：在每个受保护端点的 docstring 中追加 `**权限**: <permission_string>` 行。

**示例**：
```python
@router.put("/{alert_id}/handle")
def handle_alert(alert_id: int, ...):
    """标记告警为已处理。

    **权限**: alert:handle
    """
```

**备选方案**：在 `require_permission` 的依赖中自动注入 Swagger 描述。评估后不采用——FastAPI 的 `Depends` 不支持在 Swagger UI 中描述权限字符串，需自定义 OpenAPI hook，增加复杂度。docstring 方案简单、可维护、对 Swagger 可见（Swagger 会渲染 docstring 为 Markdown）。

### D3：错误响应声明方式

**决策**：在每个端点使用 `@router.<method>(..., responses={...})` 显式声明错误 status code + description。

**示例**：
```python
@router.post("/", response_model=AlertGroupResponse, status_code=201,
             responses={409: {"description": "名称已存在"}})
```

**理由**：FastAPI 原生支持 `responses` 参数。声明后，Swagger 会为每个端点展示可能返回的错误码及其描述，前端开发者可以据此编写错误处理逻辑。

**备选方案**：全局 `exception_handler` + 自动注入。不采用——全局 handler 虽然能返回统一格式，但 Swagger 无法自动为每个端点推断可能的错误码。

### D4：裸 dict 返回标准化

**决策**：所有返回 dict 的端点改为返回 Pydantic BaseModel，确保 Swagger 能准确渲染响应结构。

**需要修改的端点**（根据代码扫描）：
- `POST /auth/logout` → 当前返回 `{"ok": true}`，应定义 `LogoutResponse(BaseModel): ok: bool`
- `DELETE /views/{view_id}` → 当前返回 `{"ok": true}`，应定义 `DeleteResponse(BaseModel): ok: bool`
- `GET /views` → 当前返回 `{"views": [...]}`，应定义 `ViewListResponse(BaseModel): views: list[ViewResponse]`
- `GET /nodes` → 当前返回 `{"nodes": [...]}`，应定义 `NodeListResponse(BaseModel): nodes: list[NodeResponse]`
- `GET /nodes/{node_id}/videos` → 当前返回 `{"videos": [...]}`，类似处理
- `GET /nodes/{node_id}/audios` → 当前返回 `{"audios": [...]}`，类似处理
- 其他 `{"ok": true}` 端点（如 deactivate、onboard 等）

### D5：WebSocket 文档化方案

**决策**：将 WS 协议规范补充到 `openspec/specs/node-wss-connection/spec.md` 中，并确保其包含：
- 连接地址：`ws://localhost:8000/ws` 和 `ws://localhost:8000/api/v1/ws`
- 认证方式：token 查询参数
- 心跳机制：ping/pong 间隔
- 命令/响应格式：所有消息类型（ConnectRequest, ConnectResponse, UpdateStreamRequest, UpdateStreamResponse）
- 错误处理

### D6：审查顺序

**决策**：按 router 文件逐个审查，每个 router 完成 4 项检查：
1. 所有 Pydantic Field 有 description
2. 所有端点有 `response_model`（或显式 `responses`）
3. 所有端点 docstring 清晰（含 RBAC 权限标注）
4. 无 stub/TODO/NotImplementedError 残留

## Risks / Trade-offs

- **[风险] docstring 变更触发 OpenAPI schema hash 变化，可能影响前端缓存的 openapi.json** → 影响可忽略——前端目前无自动生成代码，不会受影响。
- **[风险] 新增 Pydantic Response 模型可能与现有代码路径冲突** → 每个新增模型先运行对应单元测试验证兼容性。
- **[风险] 审查工作量大（63 端点 × 17 文件）** → 分批进行，按 Tag 优先级排序（高频对接口径优先：auth → dashboard → alerts → views → events → devices → fences → exceptions → persons → users → alert-groups → detection → logs → reports → node → replay）
- **[权衡] `responses` 参数会让装饰器变长** → 可接受。可读性的微小代价换取 Swagger 文档完整性。
