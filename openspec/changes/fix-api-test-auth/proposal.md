## Why

All 46 API endpoint tests in the regression suite fail with HTTP 401 because they lack authentication headers. The `admin_headers` fixture already exists in `conftest.py` but was never wired into the individual test files. Additionally, 4 tests in `test_alert_api.py` target `/response-actions` — a route that no longer exists in the codebase. This blocks the full regression suite from being used as a quality gate.

## What Changes

- Wire `admin_headers` fixture into all API test functions across 6 test files (~46 tests)
- Delete `TestResponseActionAPI` class (4 tests) from `test_alert_api.py` — the `/response-actions` route was removed and has no corresponding API endpoint

## Capabilities

### New Capabilities
<!-- None — this is a test-infrastructure fix, not a new capability. -->

### Modified Capabilities
<!-- None — no spec-level requirement changes. -->

## Impact

- **Test files modified**: `src/tests/api/test_enum_api.py`, `test_alert_api.py`, `test_event_api.py`, `test_exception_api.py`, `test_log_api.py`, `test_user_api.py`
- **No code changes**: Production code, config, and schemas are untouched
- **No breaking changes**: All existing test assertions and behaviors are preserved; only auth headers are added
