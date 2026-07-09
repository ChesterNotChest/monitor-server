## 1. Schema 层

- [ ] 1.1 新建 `src/schema/http/enum_types.py`：定义 `EnumTypeCreate`、`EnumTypeUpdate`、`EnumTypeResponse`（id, name, created_at），供 EntityType/ActionType/SoundType/ResponseAction 共用
- [ ] 1.2 新建 `src/schema/http/alert.py`：定义 `AlertGroupCreate`、`AlertGroupUpdate`、`AlertGroupResponse`（含 responses 嵌套列表）、`ResponseBindRequest`（response_id）
- [ ] 1.3 新建 `src/schema/http/exception.py`：定义 `ExceptionCreate`（severity, group_id）、`ExceptionUpdate`、`ExceptionResponse`（含 entities/actions/sounds 嵌套）、`EntityBindRequest`、`ActionBindRequest`、`SoundBindRequest`
- [ ] 1.4 新建 `src/schema/http/event.py`：定义 `EventResponse`、`EventListResponse`（分页）、`ExceptionStatsItem`（exception_id, severity, count）、`TrendItem`（period, count）
- [ ] 1.5 更新 `src/schema/http/__init__.py` 导出所有新增 schema

## 2. Service 层 — 枚举管理

- [ ] 2.1 新建 `src/service/enum_task.py`：实现 `create_entity(db, name)`、`list_entities(db)`、`update_entity(db, id, name)`、`delete_entity(db, id)` + 同名 ActionType/SoundType 方法
- [ ] 2.2 所有 create/update 方法包含唯一性校验（IntegrityError → 409 等效异常）

## 3. Service 层 — 告警与响应

- [ ] 3.1 新建 `src/service/alert_module/__init__.py`
- [ ] 3.2 新建 `src/service/alert_module/response.py`：实现 ResponseAction CRUD：`create_response(db, name)`、`list_responses(db)`、`update_response(db, id, name)`、`delete_response(db, id)`
- [ ] 3.3 新建 `src/service/alert_module/group.py`：实现 AlertGroup CRUD：`create_group(db, name)`、`list_groups(db)`（分页 + with_responses）、`get_group(db, id)`、`update_group(db, id, name)`、`delete_group(db, id)`
- [ ] 3.4 在 `alert_module/group.py` 中实现绑定管理：`bind_response(db, group_id, response_id)`（幂等）、`unbind_response(db, group_id, response_id)`（幂等）、`get_group_responses(db, group_id)`（返回该分组的当前响应列表）
- [ ] 3.5 新建 `src/service/alert_task.py`：门户函数 `create_response_action()`、`list_response_actions()`、`update_response_action()`、`delete_response_action()`；`create_alert_group()`、`list_alert_groups()`、`get_alert_group()`、`update_alert_group()`、`delete_alert_group()`；`bind_response_to_group()`、`unbind_response_from_group()`

## 4. Service 层 — 异常规则

- [ ] 4.1 新建 `src/service/exception_module/__init__.py`
- [ ] 4.2 新建 `src/service/exception_module/binding.py`：实现 M2M 绑定管理：`bind_entity(db, exception_id, entity_id)`（幂等）、`unbind_entity(db, exception_id, entity_id)`（幂等）、`get_bound_entities(db, exception_id)`；同名 ActionType/SoundType 方法
- [ ] 4.3 新建 `src/service/exception_task.py`：门户函数 `create_exception(db, severity, group_id)`、`list_exceptions(db, severity?, page, page_size)`、`get_exception(db, id)`、`update_exception(db, id, severity?, group_id?)`、`delete_exception(db, id)`；绑定门户函数 `bind_entity_to_exception()` 等 6 个

## 5. Service 层 — 事件查询与统计

- [ ] 5.1 新建 `src/service/event_task.py`：实现 `list_events(db, view_id?, start?, end?, page, page_size)`（按时间倒序）、`get_event(db, id)`
- [ ] 5.2 实现 `stats_by_exception(db, start?, end?)`：使用 `func.count()` + `group_by ExceptionDef.id` + JOIN `ExceptionDef`，返回 `[{exception_id, severity, count}]`
- [ ] 5.3 实现 `stats_trend(db, granularity?, start?, end?)`：使用 `func.strftime()` 按 hour/day/month 聚合 + `func.count()`，返回 `[{period, count}]`

## 6. API 层 — 路由

- [ ] 6.1 新建 `src/network/api/enum_types.py`：三个 router（entity-types、action-types、sound-types），每个提供 POST/GET/{id} PUT/DELETE
- [ ] 6.2 新建 `src/network/api/alert.py`：两个 router — response-actions（独立 CRUD）+ alert-groups（CRUD + 嵌套 /{id}/responses POST/DELETE）
- [ ] 6.3 新建 `src/network/api/exception.py`：router exceptions（CRUD + 嵌套 /{id}/entities、/{id}/actions、/{id}/sounds 各 POST/DELETE）
- [ ] 6.4 新建 `src/network/api/event.py`：router events（GET 列表/详情）+ stats/by-exception + stats/trend
- [ ] 6.5 更新 `src/network/api/__init__.py`：将 4 个新路由追加到 `routers` 列表

## 7. 测试

- [ ] 7.1 新建 `src/tests/service/test_enum_task.py`：测试 EntityType/ActionType/SoundType CRUD + 唯一性冲突
- [ ] 7.2 新建 `src/tests/service/test_alert_task.py`：测试 ResponseAction CRUD、AlertGroup CRUD、绑定/解绑
- [ ] 7.3 新建 `src/tests/service/test_exception_task.py`：测试 ExceptionDef CRUD + 绑定/解绑 entities/actions/sounds
- [ ] 7.4 新建 `src/tests/service/test_event_task.py`：测试事件查询、按 exception 统计、按时间趋势
- [ ] 7.5 新建 `src/tests/api/test_enum_api.py`：测试枚举类型端点
- [ ] 7.6 新建 `src/tests/api/test_alert_api.py`：测试告警分组 + 响应动作端点
- [ ] 7.7 新建 `src/tests/api/test_exception_api.py`：测试异常规则端点
- [ ] 7.8 新建 `src/tests/api/test_event_api.py`：测试事件查询 + 统计端点
- [ ] 7.9 运行全部测试：`pytest monitor-server/src/tests/ -v`

## 8. 验证

- [ ] 8.1 删除旧数据库文件，启动应用使 SQLAlchemy 自动重建所有表
- [ ] 8.2 通过 `/docs` Swagger 页面验证全部 12 组端点可用
- [ ] 8.3 验证告警分组绑定/解绑响应动作的幂等性
- [ ] 8.4 验证异常规则绑定/解绑 AI 检测类型的幂等性
- [ ] 8.5 验证事件聚合统计结果正确
