## Context

The `api/conftest.py` already defines `admin_token` and `admin_headers` fixtures (JWT Bearer token for an "admin" user). However, none of the 46 test functions across 6 API test files accept `admin_headers` as a parameter, so every `client.post/get/put/delete` call goes without an `Authorization` header and gets rejected with HTTP 401 by the RBAC middleware.

Additionally, `test_alert_api.py::TestResponseActionAPI` (4 tests) targets `/response-actions` — an endpoint that was removed from the codebase. These tests are dead code with no corresponding route to test.

## Goals / Non-Goals

**Goals:**
- All API test functions receive `admin_headers` and pass it to every `client` call
- Dead `TestResponseActionAPI` tests removed
- Zero production code changes

**Non-Goals:**
- Adding new tests or changing existing assertions
- Fixing RBAC middleware behavior (it works correctly — rejecting unauthenticated requests)
- Changing the auth mechanism or token generation flow

## Decisions

### Decision 1: One-line fixture wiring per test function

Each test function signature changes from `def test_foo(self, client):` to `def test_foo(self, client, admin_headers):`, and every `client.xxx(...)` call gains `headers=admin_headers`.

**Rationale**: The `admin_headers` fixture is already defined and working in `conftest.py`. No new infrastructure needed. Each test file only needs mechanical wiring.

**Alternative considered**: A session-scoped `auth_client` fixture that always includes headers. Rejected because it would require changing all test functions to use a different client name ("auth_client" vs "client"), which is a larger diff with no meaningful benefit.

### Decision 2: Delete `TestResponseActionAPI` (4 tests)

The `/response-actions` route no longer exists in the API. These tests cannot be fixed by adding headers — they will fail with 404 regardless. They are dead code.

**Rationale**: There is no corresponding router, no Pydantic schema for response actions, and no CRUD operations for this concept in the current API surface. The `test_alert_api.py` file keeps its `TestAlertGroupAPI` and `TestBinding` classes (7 tests), which target the existing `/alert-groups` routes.

### Decision 3: No spec changes

This is purely test-infrastructure plumbing. No capability requirements change, no API surface changes, no behavioral changes to production code. The `openspec/specs/rbac-middleware/spec.md` requirement "endpoints must reject unauthenticated requests" is already satisfied — the tests just need to authenticate.

## Risks / Trade-offs

- **Risk**: If the admin user creation or login flow in `conftest.py` breaks, all API tests fail at setup. → **Mitigation**: The admin token fixture is already dogfooded by existing passing tests; it's a stable dependency.
- **Trade-off**: Adding `admin_headers` to test functions means the client is always authenticated as admin — role-specific tests (operator vs security_guard) would need their own fixtures. This is fine for the current test suite, which only tests CRUD access patterns that RBAC permits for the admin role.
