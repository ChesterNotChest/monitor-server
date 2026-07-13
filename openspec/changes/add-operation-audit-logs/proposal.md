# Add Operation Audit Logs

## Why

The Web log page should show more than alert-trigger records. Operators need to see who performed important system actions such as creating users, changing rules, uploading people data, handling alerts, creating/deleting views, and other write operations.

## What Changes

- Add a unified audit middleware for successful authenticated API write operations.
- Record successful login as an operation log.
- Store operation logs as `LogType.OPERATION` entries in `log_entries`.
- Keep alert-trigger logs as `LogType.ALERT`.

## Impact

- No database schema change.
- Failed requests are not logged to avoid noisy validation/auth errors.
- Log write failures are isolated and do not fail the original business request.
