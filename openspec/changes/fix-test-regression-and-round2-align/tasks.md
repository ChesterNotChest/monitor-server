## 1. 测试回归修复（首要）

- [ ] 1.1 `test_create_view_commits_view_and_streaming_state` — `response.json()["view"]["id"]` → `response.json()["id"]`
- [ ] 1.2 `test_create_view_warns_when_raw_streams_are_unavailable` — `result["warnings"][-1]` → `result.warnings[-1]`
- [ ] 1.3 运行 `pytest src/tests/service/test_view_runtime_hardening.py -v` 确认全部 4 个测试通过
- [ ] 1.4 运行 `pytest src/tests/api/ -v` 确认 API 层测试无回归

## 2. 第二轮前后端对齐 — P0（认证+仪表板）

- [ ] 2.1 打开 Swagger `/docs`，检查 `POST /auth/login` → `LoginResponse` 响应结构，对比前端 `AuthContext.tsx` 中的字段解析
- [ ] 2.2 检查 `GET /auth/me` → `UserResponse` (role: string, is_active: bool)，确认前端解析正确
- [ ] 2.3 检查 `GET /dashboard/stats` → `DashboardStats` 响应结构，对比前端 `MainDashboard.tsx`
- [ ] 2.4 检查 `GET /dashboard/trends` → `DashboardTrends` 响应结构，对比前端使用方式

## 3. 第二轮前后端对齐 — P1（视图+设备+告警）

- [ ] 3.1 检查 `POST /views` 响应（扁平 ViewResponse），对比前端 `LiveMonitor.tsx` 中对 `id` 和流 URL 的提取
- [ ] 3.2 检查 `GET /views` → `ViewListResponse {"views": [...]}`，对比前端解包逻辑
- [ ] 3.3 检查 `GET /nodes` → `NodeListResponse`、`GET /nodes/{id}/videos`、`GET /nodes/{id}/audios`，对比前端 `DeviceInfo.tsx`
- [ ] 3.4 检查 `GET /alerts`、`PUT /alerts/{id}/handle`、`PUT /alerts/{id}/false-alarm`，对比前端 `AlertContext.tsx`

## 4. 第二轮前后端对齐 — P2（事件+围栏+异常+人物）

- [ ] 4.1 检查 `GET /events`、`GET /events/{id}`、`GET /events/stats/by-exception`、`GET /events/stats/trend`，对比前端 `EventReplay.tsx` 和 `client.ts`
- [ ] 4.2 检查 `POST /fences` → FenceCreate（name, view_id, coords: number[][], dwell_time, density, leave_frames），对比前端 `FenceEditor.tsx`
- [ ] 4.3 检查 `POST /exceptions` → ExceptionCreate（group_id 非 alert_group_id），对比前端 `ExceptionSettings.tsx`
- [ ] 4.4 检查 `POST /persons`、`GET /persons`、`PUT /persons/{id}`、`DELETE /persons/{id}`、`POST /persons/{id}/avatar`，对比前端 `CharacterManagement.tsx`

## 5. 第二轮前后端对齐 — P3（用户+日志+报表+录像）

- [ ] 5.1 检查 `GET /users`、`POST /users`、`PUT /users/{id}/role`、`PUT /users/{id}/deactivate`，对比前端 `UserManagement.tsx`（注意 role 类型 int vs string）
- [ ] 5.2 检查 `GET /logs`、`GET /logs/{id}`，对比前端 `LogCenter.tsx`
- [ ] 5.3 检查 `GET /reports/weekly`、`GET /reports/monthly`，对比前端 `ReportDetail.tsx`
- [ ] 5.4 检查 `GET /views/{id}/recordings`、`GET /recordings/{id}/stream`，确认前端 `client.ts` 是否已实现

## 6. 收尾

- [ ] 6.1 汇总所有发现的不一致项，逐项修复（前端迁就后端）
- [ ] 6.2 启停 server + 前端，做一次端到端冒烟测试（登录 → 仪表板 → 至少 3 个页面）
- [ ] 6.3 更新 `前后端所有改动总结.md`，记录对齐结果和遗留问题
