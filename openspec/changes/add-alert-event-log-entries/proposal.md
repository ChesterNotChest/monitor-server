## Why

The Web log center reads `log_entries`, but real alert generation currently only creates `situation_events` and writes Python container logs. As a result, operators can see alerts in event/stat pages while the Web log page remains empty.

## What Changes

- When `AlertEngine` creates a new `SituationEvent`, also write one structured `LogEntry`.
- The log entry uses `LogType.ALERT`, links to `view_id` and `event_id`, copies the exception severity, and stores details JSON with exception and recording metadata.
- Keep Python runtime logs unchanged; this change only adds the missing DB-backed log record required by the Web log center.

## Capabilities

### Modified Capabilities

- `log-system`: real alert triggers produce DB-backed logs visible through `GET /api/v1/logs`.
- `alert-api`: newly created alert events have a corresponding structured log entry.

## Impact

- **`src/service/log_task.py`**: add `record_alert_event()` writer helper.
- **`src/service/alert_module/engine.py`**: call the writer after alert event creation and recording association.
- **Tests**: add focused service coverage for alert log entry contents.
