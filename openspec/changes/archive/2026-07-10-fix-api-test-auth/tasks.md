## 1. Fix test_enum_api.py (13 tests)

- [x] 1.1 Add `admin_headers` parameter to all 13 test function signatures in `TestEntityTypeAPI`, `TestActionTypeAPI`, `TestSoundTypeAPI`
- [x] 1.2 Pass `headers=admin_headers` to every `client.post()`, `client.get()`, `client.put()`, `client.delete()` call

## 2. Fix test_alert_api.py (11 tests → 7 tests)

- [x] 2.1 Delete `TestResponseActionAPI` class and its 4 test methods (route `/response-actions` no longer exists)
- [x] 2.2 Add `admin_headers` parameter to remaining 7 tests in `TestAlertGroupAPI` and `TestBinding`
- [x] 2.3 Pass `headers=admin_headers` to every `client` call in remaining tests

## 3. Fix test_event_api.py (5 tests)

- [x] 3.1 Add `admin_headers` parameter to all 5 test function signatures in `TestEventAPI` and `TestStatsAPI`
- [x] 3.2 Pass `headers=admin_headers` to every `client.get()` call

## 4. Fix test_exception_api.py (10 tests)

- [x] 4.1 Add `admin_headers` parameter to all 10 test function signatures in `TestExceptionAPI` and `TestBinding`
- [x] 4.2 Pass `headers=admin_headers` to every `client.post()`, `client.get()`, `client.put()`, `client.delete()` call

## 5. Fix test_log_api.py (4 tests)

- [x] 5.1 Add `admin_headers` parameter to all 4 test function signatures in `TestLogAPI`
- [x] 5.2 Pass `headers=admin_headers` to every `client.get()` call

## 6. Fix test_user_api.py (3 tests)

- [x] 6.1 Add `admin_headers` parameter to all 3 test function signatures in `TestUserAPI`
- [x] 6.2 Pass `headers=admin_headers` to every `client.post()` and `client.get()` call

## 7. Verify

- [x] 7.1 Run `pytest src/tests/api/ -v` — all 42 tests pass with 0 failures
- [x] 7.2 Run full regression `pytest src/tests/ -v` — 213 passed, 0 failures
