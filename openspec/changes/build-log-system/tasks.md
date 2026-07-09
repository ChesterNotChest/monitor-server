## 1. User 模型

- [ ] 1.1 新增 `src/constants.py`：`UserRole` IntEnum（SECURITY/ADMIN/MANAGER/OPERATOR）
- [ ] 1.2 新建 `src/models/user.py`：User 模型（id, username, role, created_at）
- [ ] 1.3 新建 `src/repository/user_repo.py`
- [ ] 1.4 更新 `src/models/__init__.py` 导入 User
- [ ] 1.5 新建 `src/schema/http/user.py`：UserCreate / UserResponse
- [ ] 1.6 新建 `src/service/user_task.py`：create_user / list_users
- [ ] 1.7 新建 `src/network/api/user.py`：POST + GET /users
- [ ] 1.8 更新 `src/network/api/__init__.py` 注册 user_router

## 2. LogEntry 模型与 Service

- [ ] 2.1 新增 `src/constants.py`：`LogType` 枚举（DEVICE/OPERATION/RECOGNITION/ALERT/SYSTEM）
- [ ] 2.2 新建 `src/models/log_entry.py`：LogEntry 模型（含所有字段 + FK）
- [ ] 2.3 新建 `src/repository/log_entry_repo.py`：带过滤的查询方法
- [ ] 2.4 更新 `src/models/__init__.py` 导入 LogEntry
- [ ] 2.5 新建 `src/schema/http/log.py`：LogEntryResponse / LogListResponse / LogStatsItem
- [ ] 2.6 新建 `src/service/log_task.py`：LogService.write() + query/stats
- [ ] 2.7 新建 `src/network/api/log.py`：GET /logs + GET /logs/stats
- [ ] 2.8 更新 `src/network/api/__init__.py` 注册 log_router

## 3. 测试

- [ ] 3.1 新建 `src/tests/service/test_log_task.py`：测试写日志 + 查询 + 统计
- [ ] 3.2 新建 `src/tests/api/test_user_api.py`：测试用户 CRUD
- [ ] 3.3 新建 `src/tests/api/test_log_api.py`：测试日志查询端点
- [ ] 3.4 运行测试：`pytest src/tests/ -v`

## 4. 验证

- [ ] 4.1 启动应用，通过 `/docs` 验证 User + Log 端点可用
- [ ] 4.2 调用 LogService.write() 写入各类型日志，验证查询和统计返回正确
