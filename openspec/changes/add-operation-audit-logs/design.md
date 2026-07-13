# Design

## Approach

Use a FastAPI middleware to observe successful mutating API requests (`POST`, `PUT`, `PATCH`, `DELETE`) under `/api/v1`. The middleware reads the bearer token, extracts the user id from JWT claims, and writes a `LogEntry` through `log_task.record_operation()`.

Login is handled directly in `auth_router.login()` because the request does not yet have a bearer token.

## Log Shape

- `log_type`: `OPERATION`
- `operator_id`: authenticated user id
- `summary`: human-readable operation summary
- `details_json`: method, path, query, status code, username, role, target type, optional target id

## Failure Handling

Operation logging is best-effort. If writing the log fails, the middleware rolls back its log session and lets the original response continue.
