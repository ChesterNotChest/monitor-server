# AI Model Capability (Delta)

## MODIFIED Requirements

### Requirement: FENCE events include fence_event_ids key

fence_engine 发布 FENCE 事件时 SHALL 包含 `fence_event_ids` 键（值为 `[result_id]` 列表），
使 AlertEngine 能通过 `_cids(FENCE, "fence_event_ids")` 正确提取围栏事件 ID。

#### Scenario: FENCE event with fence_event_ids

- **WHEN** fence_engine 发布 ENTERED/EXITED/TOO_CLOSE 事件
- **THEN** payload 包含 `"fence_event_ids": [1]`（或 [2] 对于 TOO_CLOSE）
- **AND** AlertEngine._cids 能正确提取这些 ID
