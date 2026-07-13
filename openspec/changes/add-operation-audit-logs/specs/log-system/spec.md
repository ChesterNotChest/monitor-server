## ADDED Requirements

### Requirement: Authenticated API write operations are audited
The system SHALL record successful authenticated API write operations as `OPERATION` log entries.

#### Scenario: Creating a resource writes an operation log
- **WHEN** an authenticated user successfully calls a `POST /api/v1/...` endpoint
- **THEN** the system writes an `OPERATION` log entry with `operator_id` set to the user id
- **AND** `details_json` includes method, path, status_code, action, target_type, username, and role

#### Scenario: Updating or deleting a resource writes an operation log
- **WHEN** an authenticated user successfully calls a `PUT`, `PATCH`, or `DELETE` endpoint under `/api/v1`
- **THEN** the system writes an `OPERATION` log entry for that request

#### Scenario: Failed write requests are not audited as successful operations
- **WHEN** an API write request returns a 4xx or 5xx response
- **THEN** the system SHALL NOT write a successful operation log for that request

#### Scenario: Log write failure does not fail the business request
- **WHEN** operation log persistence fails after the business request has completed
- **THEN** the original API response is still returned to the caller

### Requirement: Successful login is audited
The system SHALL record successful user login as an `OPERATION` log entry.

#### Scenario: User logs in successfully
- **WHEN** a user successfully calls `POST /api/v1/auth/login/`
- **THEN** the system writes an `OPERATION` log entry with `action=login` and `operator_id` set to the user id
