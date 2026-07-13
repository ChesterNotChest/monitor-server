# Add AI Daily Monitoring Report

## Why
The existing report API only returns weekly/monthly aggregate counters. The product requirement asks for an AI-generated daily monitoring report that summarizes recognized monitoring events and can be shown in the web UI.

## What Changes
- Add `GET /api/v1/reports/daily?date=YYYY-MM-DD`.
- Return deterministic AI-style report content generated from monitoring events, exception severity, and event distribution for the requested day.
- Include summary text, risk level, key findings, recommendations, severity distribution, top exceptions, and hourly trend.
- Keep the current weekly/monthly APIs unchanged.

## Non-Goals
- No external LLM/network dependency.
- No persisted report table in this change.
- No scheduled background delivery in this change.

## Impact
- Server API and schema expand report responses.
- Web can consume the daily report directly without fabricating a report from weekly data.
