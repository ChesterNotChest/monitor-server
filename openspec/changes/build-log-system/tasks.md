## 1. User 模型

- [x] 1.1 新增 `src/constants.py`：`UserRole` IntEnum（SECURITY/ADMIN/MANAGER/OPERATOR）
- [x] 1.2 新建 `src/models/user.py`：User 模型（id, username, role, created_at）
- [x] 1.3 新建 `src/repository/user_repo.py`
- [x] 1.4 更新 `src/models/__init__.py` 导入 User
- [x] 1.5 新建 `src/schema/http/user.py`：UserCreate / UserResponse
- [x] 1.6 新建 `src/service/user_task.py`：create_user / list_users
- [x] 1.7 新建 `src/network/api/user.py`：POST + GET /users
- [x] 1.8 更新 `src/network/api/__init__.py` 注册 user_router

## 2. LogEntry 模型与 Service

- [x] 2.1 新增 `src/constants.py`：`LogType` 枚举（DEVICE/OPERATION/RECOGNITION/ALERT/SYSTEM）
- [x] 2.2 新建 `src/models/log_entry.py`：LogEntry 模型（含所有字段 + FK）
- [x] 2.3 新建 `src/repository/log_entry_repo.py`：带过滤的查询方法
- [x] 2.4 更新 `src/models/__init__.py` 导入 LogEntry
- [x] 2.5 新建 `src/schema/http/log.py`：LogEntryResponse / LogListResponse / LogStatsItem
- [x] 2.6 新建 `src/service/log_task.py`：LogService.write() + query/stats
- [x] 2.7 新建 `src/network/api/log.py`：GET /logs + GET /logs/stats
- [x] 2.8 更新 `src/network/api/__init__.py` 注册 log_router

## 3. 测试

- [x] 3.1 新建 `src/tests/service/test_log_task.py`：测试写日志 + 查询 + 统计
- [x] 3.2 新建 `src/tests/api/test_user_api.py`：测试用户 CRUD
- [x] 3.3 新建 `src/tests/api/test_log_api.py`：测试日志查询端点
- [x] 3.4 运行测试：`pytest src/tests/ -v`

## 4. 验证

- [ ] 4.1 启动应用，通过 `/docs` 验证 User + Log 端点可用
- [x] 4.2 调用 LogService.write() 写入各类型日志，验证查询和统计返回正确
