## MODIFIED Requirements

### Requirement: 周报与月报
系统 SHALL continue to provide weekly and monthly report endpoints.

- `GET /api/v1/reports/weekly`
- `GET /api/v1/reports/monthly`

#### Scenario: Existing weekly and monthly endpoints remain available
- **WHEN** a client requests the weekly or monthly report endpoint
- **THEN** the system returns the existing aggregate report shape with total alerts, severity distribution, and top exceptions

### Requirement: AI daily monitoring report
系统 SHALL provide `GET /api/v1/reports/daily`. The endpoint SHALL accept an optional `date=YYYY-MM-DD` query parameter and return a deterministic AI-style daily monitoring report generated from persisted monitoring events for that day.

The response SHALL include:
- `period`
- `date`
- `total_alerts`
- `risk_level`
- `summary`
- `key_findings`
- `recommendations`
- `by_severity`
- `top_exceptions`
- `hourly_trend`

#### Scenario: Generate empty daily report
- **WHEN** no monitoring events exist for the requested date
- **THEN** the response has `total_alerts=0`
- **AND** `risk_level` is `LOW`
- **AND** the summary states that no alerts were detected for the day

#### Scenario: Generate daily report with alerts
- **WHEN** monitoring events exist for the requested date
- **THEN** the response groups alerts by severity
- **AND** includes top exception categories
- **AND** includes hourly trend points
- **AND** includes recommendations derived from the highest risk level and frequent exceptions

#### Scenario: Date defaults to today
- **WHEN** `date` is omitted
- **THEN** the system generates a report for the server's current local date
