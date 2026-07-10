## 1. 测试回归修复（首要）

- [x] 1.1 `test_create_view_commits_view_and_streaming_state` — `response.json()["view"]["id"]` → `response.json()["id"]`
- [x] 1.2 `test_create_view_warns_when_raw_streams_are_unavailable` — `result["warnings"][-1]` → `result.warnings[-1]`
- [x] 1.3 运行 `pytest src/tests/service/test_view_runtime_hardening.py -v` 确认全部 4 个测试通过
- [x] 1.4 运行 `pytest src/tests/api/ -v` 确认 API 层测试无回归（42 passed）

## 2. 第二轮前后端对齐 — P0（认证+仪表板）

- [x] 2.1 Auth login: 前端 LoginRequest {username, password} JSON body → 后端 auth_router 接受 Pydantic LoginRequest body ✓ 一致
- [x] 2.2 Auth me: 前端 UserResponse {role: string, is_active: bool} → 后端 auth_schema.UserResponse 一致 ✓
- [x] 2.3 Dashboard stats: 前端 DashboardStats {total_views, active_alerts, online_nodes, total_devices} → 后端一致 ✓
- [x] 2.4 Dashboard trends: 前端 DashboardTrends {points: [{date, severity, count}]} → 后端一致 ✓

## 3. 第二轮前后端对齐 — P1（视图+设备+告警）

- [x] 3.1 Views POST: 前端 POST /views JSON body {audio_id, video_id} → 后端 ViewCreateRequest body 一致 ✓（扁平 ViewResponse 响应已对齐）
- [x] 3.2 Views list: 前端处理 GET /views → {"views": [...]} 解包 → 后端 ViewListResponse 一致 ✓
- [x] 3.3 Nodes: 前端处理 {"nodes": [...]}, {"videos": [...]}, {"audios": [...]} 解包 → 后端一致 ✓
- [x] 3.4 Alerts: 前端 fetchAlerts/markHandled/markFalseAlarm → 后端一致 ✓

## 4. 第二轮前后端对齐 — P2（事件+围栏+异常+人物）

- [x] 4.1 Events: 前端 client.ts 已实现 GET /events, /events/{id}, /events/stats/* → 后端一致 ✓
- [x] 4.2 Fences: 前端 FenceCreate {name, view_id, coords: number[][], dwell_time?, density?, leave_frames?} → 后端 fence_schema 一致 ✓
- [x] 4.3 Exceptions: 前端 ExceptionCreate 使用 `group_id`（非 alert_group_id）→ 后端一致 ✓。修复了 ExceptionResponse 缺失嵌套字段（+AlertGroupRef +DetectionTypeRef）
- [x] 4.4 Persons: 前端 PersonCreate/Update/Response + upload → 后端一致 ✓

## 5. 第二轮前后端对齐 — P3（用户+日志+报表+录像）

- [x] 5.1 Users: DB 存 role 为 string（security_guard/manager/operator），API 返回 string。前端 string role 正确 ✓。后端 user.py schema 的 int role 描述已修正为 string
- [x] 5.2 Logs: 前端 fetchLogs/fetchLogById → 后端一致 ✓
- [x] 5.3 Reports: 前端 fetchWeeklyReport/fetchMonthlyReport → 后端一致 ✓
- [x] 5.4 Recordings: 前端 client.ts 已实现 listRecordings/streamRecording → 后端一致 ✓

## 6. 收尾

- [x] 6.1 汇总不一致项并修复：
  - **后端修复**：user.py UserCreate/UserResponse 的 role 字段从 int 改为 str（匹配 DB 和实际 API 行为）
  - **前端修复**：types.ts ExceptionResponse 补充 alert_group/entities/actions/sounds 嵌套字段，新增 AlertGroupRef 和 DetectionTypeRef 类型
  - **无 CRITICAL 不一致**：Auth、Dashboard、Views、Nodes、Alerts、Fences、Exceptions、Persons、Logs、Reports、Recordings 全部 11 个模块已对齐
- [ ] 6.2 启停 server + 前端，做一次端到端冒烟测试（登录 → 仪表板 → 至少 3 个页面）
- [ ] 6.3 更新 `前后端所有改动总结.md`，记录对齐结果和遗留问题

### 对齐结果总结

| 模块 | 状态 | 备注 |
|------|------|------|
| Auth | ✅ 一致 | LoginRequest/Response 字段完全匹配 |
| Dashboard | ✅ 一致 | Stats + Trends 完全匹配 |
| Views | ✅ 一致 | 扁平 ViewResponse 已对齐，ViewListResponse 包裹正确 |
| Nodes/Devices | ✅ 一致 | NodeListResponse 等包裹格式一致 |
| Alerts | ✅ 一致 | 列表 + handle/false-alarm 一致 |
| Events | ✅ 一致 | 4 个端点均已实现 |
| Fences | ✅ 一致 | FenceCreate 全部字段匹配 |
| Exceptions | ✅ 已修复 | 补全 ExceptionResponse 嵌套字段 |
| Persons | ✅ 一致 | CRUD + avatar upload 一致 |
| Users | ✅ 已修复 | role 类型确认为 string（非 int），后端 schema 已修正 |
| Logs | ✅ 一致 | 列表 + 详情一致 |
| Reports | ✅ 一致 | Weekly + Monthly 一致 |
| Recordings | ✅ 一致 | 列表 + stream 一致 |

### 遗留问题
- EventReplay 页面的"设为已处理"/"设为误报"按钮使用的是 event.id 调用 alert 端点，两者 ID 空间不同——可能需要讨论设计意图
