## 1. Specify Behavior

- [x] Add OpenSpec change artifacts for DB-backed alert event logs.

## 2. Implement Writer

- [x] Add `log_task.record_alert_event()` for structured alert log entries.
- [x] Call the writer from `AlertEngine` after a new alert event is persisted.

## 3. Verify

- [x] Add focused service test coverage for alert log entry content.
- [x] Run focused logging and alert tests.
