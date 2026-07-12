## Context

当前 `create_view()` 正确调用了 `build_play_urls()` 并构造带 URL 的 `ViewResponse`。但 `get_view()` 和 `list_views()` 直接返回 ORM 对象（`MonitorView`），该数据库模型没有 `flv_url`/`webrtc_url`/`rtmp_url` 列，因此 Pydantic 序列化时这些字段全部为 `None`。`ViewResponse` schema 已定义这三个字段（`from_attributes=True`），问题仅在 service 层未填充。

此外，SRS 的 `http_server` 配置缺少 `crossdomain on;`，浏览器会拦截前端对 SRS `:8080` 的跨域请求。

`build_play_urls()` 本身逻辑正确——`DEBUG_WEB_STREAM=false` 时基于 `SRS_HOST`/`SRS_HTTP_PORT` 等配置构建三个 URL。无需修改此函数。

## Goals / Non-Goals

**Goals:**
- 修复 `get_view()` 和 `list_views()` 返回正确的流媒体 URL
- SRS 配置支持前端跨域访问
- 验证回放流端点行为正确

**Non-Goals:**
- 不改变 `build_play_urls()` 的 URL 构建逻辑
- 不改变数据库 schema（URL 不持久化，每次都动态构建）
- 不涉及前端 WebRTC WHEP 播放器改造（那是前端的工作）
- 不涉及 AI 管线变更

## Decisions

### Decision 1: Service 层填充 URL（而非 Router 层或 Schema 层）

**选择**：在 `view_task.py` 的 `get_view()` / `list_views()` 中调用 `build_play_urls()`，构造 `ViewResponse` 对象返回。

**替代方案**：
- *Router 层填充*：在 `view_router.py` 的 endpoint handler 中调用 `build_play_urls()` 后修改响应。❌ 违反 network/api 不包含业务逻辑的分层约定。
- *Schema validator 层*：给 `ViewResponse` 添加 `@field_validator` 动态生成 URL。❌ Schema 不应依赖 `settings` 和网络配置；且 `list_views` 需要为列表中每个 View 单独构建 URL，validator 不适合批量操作。
- *ORM 模型添加 hybrid_property*：❌ ORM 不应依赖 `settings` 全局状态，违反了数据层独立性。

**结论**：Service 层是最合适的位置——`create_view()` 已经在这里做了同样的事，保持一致性。

### Decision 2: URL 不持久化

**选择**：每次查询时动态调用 `build_play_urls(view_id)`，不存储 URL 到数据库。

**理由**：
- URL 依赖于运行时配置（`SRS_HOST`、`SRS_PUBLIC_HOST` 等），配置变更后数据库中的旧 URL 会失效
- `create_view()` 已经采用此模式（只在返回响应时填充 URL，不写入 DB）
- 性能影响可忽略（`build_play_urls()` 是纯字符串拼接，无 I/O）

### Decision 3: `list_views()` 返回 `ViewResponse` 列表而非 ORM 列表

**选择**：将 `list_views()` 的返回类型从 ORM 对象列表改为 `list[ViewResponse]`，对齐 `create_view()` 的返回类型。

**影响**：调用方 `view_router.py` 中 `GET /views` 的 endpoint handler 可能不需要改（`ViewResponse.model_validate` 或直接返回 Pydantic 对象均可被 FastAPI 正确序列化），但类型签名更清晰。

## Risks / Trade-offs

- **[低风险] `list_views` 性能**：每个 View 调用一次 `build_play_urls()`（纯字符串拼接），View 数量通常 < 100，不会有性能问题。
- **[低风险] `DEBUG_WEB_STREAM` 配置不一致**：如果忘记将 `DEBUG_WEB_STREAM` 设为 `false`，前端仍会收到 `flv_url: null`。→ 日志中已有警告横幅；前端也需展示明确提示（前端侧已在已知问题中标记）。
