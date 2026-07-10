## 1. Register event router (code fix)

- [x] 1.1 Add `from .event import router as event_router, stats_router` to `api/__init__.py`
- [x] 1.2 Add `event_router` and `stats_router` to the `routers` list
- [x] 1.3 Run existing event service tests to confirm routes work

## 2. Archive delta specs

- [x] 2.1 Archive `event-query-api` delta — routes now registered
- [x] 2.2 Archive `alert-group-crud-api` delta — ResponseAction + bind routes removed
- [x] 2.3 Archive `alert-group-api` delta — ResponseAction references + GET-by-ID removed
- [x] 2.4 Archive `exception-crud-api` delta — bind/unbind + GET-by-ID + severity filter removed
- [x] 2.5 Archive `exception-api` delta — severity filter claim removed
- [x] 2.6 Archive `enum-crud-api` delta — route prefixes fixed, GET-by-ID + duplicate-409 removed
- [x] 2.7 Archive `log-api` delta — "按级别/时间范围筛选" removed (filter not implemented)

## 3. Verify

- [x] 3.1 Run `pytest src/tests/api/ -v` — all 42 tests pass (no regressions)
- [x] 3.2 Run `pytest src/tests/service/test_event_task.py -v` — event service tests pass (6/6)
- [x] 3.3 Verify event routes appear in `/docs` Swagger UI (manual check optional)
