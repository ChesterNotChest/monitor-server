## ADDED Requirements

### Requirement: Daily report endpoints with persistence
系统 SHALL 提供日报的持久化读写端点。

- `GET /api/v1/reports/daily/?date=YYYY-MM-DD` — 返回持久化的日报（含 `stats_json` 和 `insights_json`）。无持久化数据时回退实时计算
- `POST /api/v1/reports/daily/generate-now/` — 手动触发即时日报生成（范围 00:00~now CST），持久化并返回
- `POST /api/v1/reports/daily/deepseek/`（已有，保留）— 手动用自定义 key 生成 AI 洞察并返回（不持久化，用于测试/预览）
- 响应新增字段：`stats`（统计层），`insights`（洞察层，可为 null），`generated_at`，`regenerated_count`，`next_scheduled_at`（下次定时生成时间）

#### Scenario: Fetch persisted daily report
- **WHEN** 客户端 GET `/daily/?date=2026-07-14`
- **THEN** 若有持久化数据则返回带 `stats` 和 `insights` 的完整响应；若无则实时计算并返回无 `insights` 的基础版本

#### Scenario: Manual instant generation
- **WHEN** 客户端 POST `/daily/generate-now/`
- **THEN** 系统生成日报、持久化、返回完整数据。响应 header 或 body 中标注 `generated_now: true`

### Requirement: Report settings endpoint
系统 SHALL 提供报告配置读写端点。

- `GET /api/v1/reports/settings/` — 返回脱敏的 API Key 状态和下次定时生成时间
- `PUT /api/v1/reports/settings/` — 更新 API Key（用户覆盖值）

#### Scenario: Configure API key
- **WHEN** 客户端 PUT `{ "api_key": "sk-newkey" }`
- **THEN** 后续日报自动使用该 key 调用 DeepSeek

### Requirement: Weekly report with snapshot
周报端点 SHALL 返回持久化快照（优先）或实时计算（回退）。

- `GET /api/v1/reports/weekly/` — 若 `weekly_reports` 表有本周快照则直接返回，否则实时计算并返回
- 响应新增字段：`week_start`, `week_end`, `daily_breakdown`（7 天数组）

#### Scenario: Snapshot available
- **WHEN** 本周的周报快照已生成
- **THEN** 直接返回持久化数据，响应时间 < 50ms

#### Scenario: No snapshot, fallback
- **WHEN** 本周快照不存在（周一凌晨前访问）
- **THEN** 系统实时计算当前周数据并返回，标记 `"snapshot": false`

## MODIFIED Requirements

### Requirement: 周报与月报
系统 SHALL 提供报表端点，聚合指定周期的告警统计、设备状态、异常趋势。仅负责人可访问。周报优先返回持久化快照，月报实时计算。

- `GET /api/v1/reports/weekly/` — 本周报告（优先返回持久化快照，含各天分段统计）
- `GET /api/v1/reports/monthly/` — 本月报告（实时计算，含趋势对比）
- 周报/月报响应新增 `daily_breakdown` 字段（各天告警数数组）
