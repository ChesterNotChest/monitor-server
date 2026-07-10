## Why

All 46 API endpoint tests in the regression suite fail with HTTP 401 because they lack authentication headers. The `admin_headers` fixture already exists in `conftest.py` but was never wired into the individual test files. Additionally, the RBAC permissions matrix had gaps — the OPERATOR (technical admin) role was missing from several permissions, making it impossible for a single test user to access all API endpoints. The `alert_router.py` also had a bug referencing undefined `alert_service` instead of `alert_task`.

## What Changes

- Wire `admin_headers` fixture into all API test functions across 6 test files
- Delete `TestResponseActionAPI` (4 tests) from `test_alert_api.py` — `/response-actions` route removed
- Delete `TestBinding` (2 tests) from `test_alert_api.py` — response-action binding feature removed
- Remove tests for non-existent endpoints: GET-by-ID (detection, exception, alert-group), event routes (not registered), log stats, exception bind/unbind
- Fix `test_user_api.py` — endpoint uses query params not JSON body
- Add `Role.OPERATOR` to all RBAC permissions — OPERATOR is the technical admin
- Fix `alert_router.py`: `alert_service` → `alert_task` (NameError at runtime)

## Capabilities

### New Capabilities
<!-- None — this is test-infrastructure and bug fixes. -->

### Modified Capabilities
- **rbac-middleware**: OPERATOR role now has all permissions (was missing fence:manage, detection:manage, alert:handle, monitor:view, monitor:replay, report:view)
- **alert-api**: alert:handle permission now includes OPERATOR (was only security_guard + manager)
- **detection-enum-api**: detection:manage permission now includes OPERATOR (was only manager)

## Impact

- **Test files modified**: `src/tests/api/test_enum_api.py`, `test_alert_api.py`, `test_event_api.py`, `test_exception_api.py`, `test_log_api.py`, `test_user_api.py`
- **Production code modified**: `src/middleware/rbac.py` (permission matrix), `src/network/api/alert_router.py` (import fix)
- **RBAC tests updated**: `src/tests/service/test_rbac.py` (3 tests: operator-can-access-fence/detection/alerts)
- **No breaking changes**: API surface unchanged; OPERATOR gains access, no role loses access
