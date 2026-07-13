# Electronic Fence Model (Delta)

## MODIFIED Requirements

### Requirement: ElectronicFence includes safe_distance and entry_delay_seconds

`ElectronicFence` 模型 SHALL 在现有字段外增加：
- `safe_distance`: `Integer, default=0` — 安全距离（像素），0 表示禁用 TOO_CLOSE
- `entry_delay_seconds`: `Integer, default=0` — 停留秒数，0 表示立即触发

`dwell_time` 和 `density` 字段 SHALL 保持向后兼容，但不再作为围栏检测的核心逻辑。

#### Scenario: Legacy fence data

- **WHEN** 数据库中已存在的围栏记录不含新字段
- **THEN** `safe_distance` 和 `entry_delay_seconds` 使用默认值 0
