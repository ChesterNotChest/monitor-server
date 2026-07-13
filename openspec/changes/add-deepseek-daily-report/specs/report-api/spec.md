## MODIFIED Requirements

### Requirement: AI daily monitoring report
The system SHALL continue to provide `GET /api/v1/reports/daily` as an authenticated deterministic local daily report endpoint.

#### Scenario: Local daily report remains available
- **WHEN** a client requests `GET /api/v1/reports/daily`
- **THEN** the system returns a daily report without requiring an external AI token

### Requirement: DeepSeek daily report generation
The system SHALL provide an authenticated `POST /api/v1/reports/daily/deepseek` endpoint that generates a daily monitoring report through DeepSeek chat completions using a user-provided API key.

The endpoint SHALL:
- accept `date`, `api_key`, and optional `model` in the JSON request body
- use the local daily report aggregation as structured context
- call DeepSeek's OpenAI-compatible chat completions API
- return the daily report response shape with AI metadata
- avoid persisting or logging the API key

#### Scenario: Generate report with user key
- **WHEN** the client submits a valid DeepSeek API key and date
- **THEN** the server calls DeepSeek with structured daily monitoring context
- **AND** returns model-generated `summary`, `key_findings`, and `recommendations`
- **AND** includes provider/model metadata in the response

#### Scenario: Missing key is rejected
- **WHEN** `api_key` is empty or missing
- **THEN** the endpoint returns a client error
- **AND** the deterministic local report endpoint remains usable

#### Scenario: DeepSeek call fails
- **WHEN** DeepSeek is unreachable or returns an invalid response
- **THEN** the endpoint returns a clear client-facing error
- **AND** the API key is not stored
