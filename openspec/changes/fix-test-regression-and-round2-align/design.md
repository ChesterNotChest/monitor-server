## Context

`complete-server-endpoints` 变更将 `view_task.create_view()` 返回值从 dict 改为 `ViewResponse` Pydantic model。HTTP 响应 JSON 从 `{"view": {"id": 1, ...}, "srs_urls": {...}, "warnings": [...]}` 变为扁平结构 `{"id": 1, "audio_id": 1, ..., "warnings": [...]}`。两个测试仍用 dict 下标访问，因此失败。

---

## Part A: 测试回归修复

### 根因分析

**测试 1** `test_create_view_commits_view_and_streaming_state`:
```python
# Line 58 — 旧: response.json() 是 {"view": {"id": 1, ...}, ...}
view_id = response.json()["view"]["id"]
# 新结构: response.json() 是 ViewResponse 扁平字段
# 修复: response.json()["id"]

# Line 60 — GET /views 返回 ViewListResponse {"views": [...]}
listed = client.get("/api/v1/views/").json()["views"]
# 此结构未变，但需确认 ViewListResponse 正确序列化
```

**测试 2** `test_create_view_warns_when_raw_streams_are_unavailable`:
```python
# Line 91-94 — create_view() 现在返回 ViewResponse (Pydantic model)
result = view_task.create_view(db, audio_id=audio.id, video_id=video.id)
assert "Raw stream(s) not ready for merge" in result["warnings"][-1]
# 修复: result.warnings[-1]  (属性访问，非 dict 下标)
```

### 修复方案

| 位置 | 旧代码 | 新代码 |
|------|--------|--------|
| Line 58 | `response.json()["view"]["id"]` | `response.json()["id"]` |
| Line 60 | `client.get("/api/v1/views/").json()["views"]` | 不变（ViewListResponse 保留 `views` 包裹） |
| Line 63 | `client.get("/api/v1/nodes/1/videos").json()["videos"]` | 不变（VideoDeviceListResponse 保留 `videos` 包裹） |
| Line 94 | `result["warnings"][-1]` | `result.warnings[-1]` |

---

## Part B: 第二轮前后端对齐

### 对齐策略

以当前 Swagger (`/docs`) 和 server 代码为唯一标准，逐模块检查前端 API 调用：

1. **请求参数对齐**：前端发送的 method、path、query params、body 是否与 Swagger 一致
2. **响应结构对齐**：前端解析的 JSON 字段路径是否与 server 实际返回匹配
3. **错误处理对齐**：前端是否有对应各 HTTP 错误码的处理逻辑
4. **缺失端点补齐**：前端 client.ts 是否覆盖了 server 所有端点

### 对齐检查清单（按模块优先级）

| 优先级 | 模块 | 前端文件 | 后端 Router | 上次 explore 发现的问题 |
|--------|------|---------|-------------|------------------------|
| P0 | Auth | `AuthContext.tsx` | `auth_router.py` | UserResponse 字段匹配 |
| P0 | Dashboard | `MainDashboard.tsx` | `dashboard_router.py` | 无已知问题 |
| P1 | Views | `LiveMonitor.tsx` | `view_router.py` | 响应已变平（本次修复的关联） |
| P1 | Devices/Nodes | `DeviceInfo.tsx` | `node_router.py` + `device_router.py` | 包裹响应解包 |
| P1 | Alerts | `AlertContext.tsx` | `alert_router.py` | 无已知问题 |
| P2 | Events | `EventReplay.tsx` | `event.py` | 前端可能缺事件端点 |
| P2 | Fences | `FenceEditor.tsx` | `fence_router.py` | FenceCreate 字段对齐 |
| P2 | Exceptions | `ExceptionSettings.tsx` | `exception_router.py` | group_id 字段名 |
| P2 | Persons | `CharacterManagement.tsx` | `named_person.py` | 无已知问题 |
| P3 | Users | `UserManagement.tsx` | `user_router.py` | role 类型 (string vs int) |
| P3 | Logs | `LogCenter.tsx` | `log_router.py` | 无已知问题 |
| P3 | Reports | `ReportDetail.tsx` | `report_router.py` | 无已知问题 |
| P3 | Recordings | 前端可能缺失 | `replay.py` | 前端是否实现 |

### 决策：对齐方式

- 每次发现不一致时，**前端迁就后端**——后端 Swagger 为标准
- 前端修改仅限于 `types.ts`、`client.ts` 和相关 page 文件
- 不对服务器端行为做任何修改（除非发现 server 端 bug）
