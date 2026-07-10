## 1. 基础设施：通用响应模型

- [x] 1.1 新增 `schema/http/common.py`，定义通用响应模型：`OkResponse`（`{ ok: bool }`）、`DeleteResponse`（`{ ok: bool }`）、`StatusResponse`（`{ status: str }`）
- [x] 1.2 在 `schema/http/__init__.py` 中导出通用响应模型

## 2. Schema Field Description 补全（按优先级排序）

- [x] 2.1 审查 `schema/http/auth_schema.py` —— UserResponse 各字段补充 description
- [x] 2.2 审查 `schema/http/alert_schema.py` —— AlertResponse 各字段补充 description（id, view_id, exception_id, recording_id, timestamp）
- [x] 2.3 审查 `schema/http/dashboard_schema.py` —— DashboardStats、AlertTrendPoint 各字段补充 description
- [x] 2.4 审查 `schema/http/view_schema.py` —— ViewCreateRequest、ViewResponse 各字段补充 description（含 flv_url、webrtc_url、rtmp_url、warnings 的含义）
- [x] 2.5 审查 `schema/http/fence_schema.py` —— FenceCreate 各字段补充 description（coords 格式说明、dwell_time/density/leave_frames 含义和默认值）
- [x] 2.6 审查 `schema/http/exception.py` —— ExceptionCreate、ExceptionResponse（含嵌套 EnumTypeRef、AlertGroupRef）各字段补充 description
- [x] 2.7 审查 `schema/http/event.py` —— EventResponse、ExceptionStatsItem、TrendItem 各字段补充 description
- [x] 2.8 审查 `schema/http/named_person.py` —— PersonCreate、PersonUpdate、PersonResponse 各字段补充 description
- [x] 2.9 审查 `schema/http/user.py` —— UserResponse 各字段补充 description（role 字段说明 1-4 含义）
- [x] 2.10 审查 `schema/http/alert.py` 和 `schema/http/alert_group_schema.py` —— AlertGroupCreate/Response、ResponseAction 等字段补充 description
- [x] 2.11 审查 `schema/http/device_schema.py`、`schema/http/node_schema.py` —— NodeHealthResponse、VideoDeviceResponse、AudioDeviceResponse 各字段补充 description
- [x] 2.12 审查 `schema/http/detection_schema.py`、`schema/http/enum_types.py` —— DetectionTypeCreate/Response、EnumTypeCreate/Response 各字段补充 description
- [x] 2.13 审查 `schema/http/log.py`、`schema/http/log_schema.py` —— LogEntry 各字段补充 description
- [x] 2.14 审查 `schema/http/report_schema.py` —— ReportResponse 各字段补充 description
- [x] 2.15 审查 `schema/http/replay.py` —— RecordingResponse 各字段补充 description

## 3. 响应模型标准化（消除裸 dict）

- [x] 3.1 `POST /auth/logout` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.2 `DELETE /views/{view_id}` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.3 `GET /views` —— 新增 `ViewListResponse(BaseModel): views: list[ViewResponse]`，替换裸 `{"views": [...]}`
- [x] 3.4 `GET /nodes` —— 新增 `NodeListResponse(BaseModel): nodes: list[NodeResponse]`，替换裸 `{"nodes": [...]}`
- [x] 3.5 `GET /nodes/{node_id}/videos` —— 新增 `VideoDeviceListResponse(BaseModel): videos: list[VideoDeviceResponse]`，替换裸 `{"videos": [...]}`
- [x] 3.6 `GET /nodes/{node_id}/audios` —— 新增 `AudioDeviceListResponse(BaseModel): audios: list[AudioDeviceResponse]`，替换裸 `{"audios": [...]}`
- [x] 3.7 `PUT /alerts/{alert_id}/handle` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.8 `PUT /alerts/{alert_id}/false-alarm` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.9 `PUT /users/{user_id}/deactivate` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.10 `POST /devices/nodes/{node_id}/onboard` —— 使用 `OkResponse` 替换裸 `{"ok": true}`
- [x] 3.11 检查所有其他返回 dict 的端点，统一使用通用响应模型

## 4. 错误响应声明

- [x] 4.1 auth router —— 补全 `responses={...}`（login: 401, me: 401）
- [x] 4.2 alert router —— 补全 `responses={...}`（handle/false-alarm: 404）
- [x] 4.3 alert group router —— 补全 `responses={...}`（create: 409, update/delete: 404）
- [x] 4.4 dashboard router —— 确认无额外错误声明需求（当前仅 200）
- [x] 4.5 detection router —— 补全 `responses={...}`（create: 409, update/delete: 404）
- [x] 4.6 device router —— 补全 `responses={...}`（health: 404, onboard: 404）
- [x] 4.7 event router —— 补全 `responses={...}`（get_one: 404, stats: 422 for bad granularity）
- [x] 4.8 exception router —— 补全 `responses={...}`（create/update: 404 for bad group_id, delete: 404）
- [x] 4.9 fence router —— 补全 `responses={...}`（create: 404 for bad view_id, update/delete: 404）
- [x] 4.10 log router —— 补全 `responses={...}`（get_by_id: 404）
- [x] 4.11 named person router —— 补全 `responses={...}`（create: 409, get/update/delete: 404, avatar: 404/422）
- [x] 4.12 node router —— 补全 `responses={...}`（videos/audios: 404 for bad node_id）
- [x] 4.13 replay router —— 补全 `responses={...}`（stream: 404）
- [x] 4.14 report router —— 确认无额外错误声明需求
- [x] 4.15 user router —— 补全 `responses={...}`（create: 400/409, role: 400/404, deactivate: 404）
- [x] 4.16 view router —— 补全 `responses={...}`（create: 404, get/delete: 404）

## 5. RBAC 权限 Docstring 标注

- [x] 5.1 alert router —— 为 handle、false-alarm 端点 docstring 添加 `**权限**: alert:handle`
- [x] 5.2 alert group router —— 为全部 4 端点 docstring 添加 `**权限**: alert_group:manage`
- [x] 5.3 dashboard router —— 为全部 2 端点 docstring 添加 `**权限**: dashboard:view`
- [x] 5.4 detection router —— 为全部 12 端点 docstring 添加 `**权限**: detection:manage`
- [x] 5.5 device router —— 为全部 3 端点 docstring 添加对应权限（device:list, device:health, device:onboard）
- [x] 5.6 exception router —— 为全部 4 端点 docstring 添加 `**权限**: exception:manage`
- [x] 5.7 fence router —— 为全部 4 端点 docstring 添加 `**权限**: fence:manage`
- [x] 5.8 log router —— 为全部 2 端点 docstring 添加 `**权限**: log:view`
- [x] 5.9 report router —— 为全部 2 端点 docstring 添加 `**权限**: report:view`
- [x] 5.10 user router —— 为全部 4 端点 docstring 添加 `**权限**: user:manage`

## 6. Swagger Tag 整理

- [x] 6.1 event.py —— 将 `stats_router` 的 `tags=["事件统计"]` 改为 `tags=["事件日志"]`，与主 router 统一
- [x] 6.2 全局审查所有 router 的 Tag 命名一致性（中文、无拼写错误、同一业务域同一 Tag）

## 7. WebSocket 协议文档完善

- [x] 7.1 审查 `openspec/specs/node-wss-connection/spec.md` 覆盖：连接地址、认证方式（token 参数）、心跳机制、所有消息类型（ConnectRequest/Response、UpdateStreamRequest/Response、Heartbeat）、错误格式
- [x] 7.2 补充缺失的协议细节（心跳间隔 30s、超时 90s、错误消息格式、WebSocket 关闭码 4001）
- [x] 7.3 确认 `schema/wss/node_commands.py` 中的 Pydantic 模型与 spec.md 中的协议描述一致

## 8. 端点实现完整性验证

- [x] 8.1 运行所有 API 测试用例 —— 42 passed，无 NotImplementedError 或 TODO stub
- [x] 8.2 搜索全项目 `# TODO` 和 `NotImplementedError` —— 仅 1 处非关键 TODO 注释（`models/response_action.py`，非 API 路径）
- [x] 8.3 （需手动）启动 server 并打开 `/docs`，遍历每个端点验证 Swagger 渲染效果

## 9. 最终验证（需手动完成）

- [ ] 9.1 启动 server (`python -m src.run`)
- [ ] 9.2 打开 `http://localhost:8000/docs`，逐 Tag 逐端点检查：field description 可见、response 结构完整、error responses 列出、权限标注清晰
- [ ] 9.3 使用 Swagger "Try it out" 功能对每个端点发起实际请求，验证响应结构与 Swagger 声明一致
