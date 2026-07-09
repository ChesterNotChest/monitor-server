# Report API

**Purpose:** 周报/月报聚合——仅负责人可访问。

## Requirements

### Requirement: 周报与月报
系统 SHALL 提供报表端点，聚合指定周期的告警统计、设备状态、异常趋势。仅负责人可访问。

- `GET /api/v1/reports/weekly` — 本周报告（含告警数、按严重级别分布、Top 5 异常类型）
- `GET /api/v1/reports/monthly` — 本月报告（同上 + 趋势对比）
