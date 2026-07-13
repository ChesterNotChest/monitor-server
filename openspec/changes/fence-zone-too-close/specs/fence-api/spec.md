# Fence API (Delta)

## MODIFIED Requirements

### Requirement: FenceCreate/Response includes safe_distance and entry_delay_seconds

`FenceCreate` 和 `FenceResponse` schema SHALL 新增 `safe_distance`（默认 0）和 `entry_delay_seconds`（默认 0）。

#### Scenario: Create fence with safe distance

- **WHEN** POST `/api/v1/fences/` 携带 `{"safe_distance": 50, "entry_delay_seconds": 5, ...}`
- **THEN** 响应包含 `safe_distance: 50, entry_delay_seconds: 5`
