## Design

The existing `LogEntry` model already supports the required fields: `log_type`, `view_id`, `event_id`, `severity`, `summary`, and `details_json`. The smallest reliable integration is to write a single log entry at the point where AlertEngine has successfully created a `SituationEvent`.

`log_task.record_alert_event()` centralizes formatting:

- `log_type`: `LogType.ALERT`
- `summary`: `告警触发：{exception_name}`
- `view_id`: event view
- `event_id`: situation event ID
- `severity`: exception severity integer
- `details_json`: action, exception ID/name, view ID, event ID, severity name, and recording ID

The AlertEngine call is wrapped so a logging failure is recorded through Python logging and does not prevent WSS broadcast or the alert event itself.

## Non-Goals

- Do not mirror all Python application logs into `log_entries`.
- Do not add log filters or stats endpoints.
- Do not change the Web log page.
- Do not alter recognition, recording, or WSS behavior beyond adding the DB log entry.
