## ADDED Requirements

### Requirement: Daily report persistence
系统 SHALL 将每日监控报告持久化到 `daily_reports` 表，包含统计层数据和可选的 AI 洞察层数据。

- `daily_reports` 表字段：`id`, `report_date`（唯一）, `stats_json`（TEXT, NOT NULL）, `insights_json`（TEXT, NULLABLE）, `ai_provider`（VARCHAR, NULLABLE）, `ai_model`（VARCHAR, NULLABLE）, `regenerated_count`（INTEGER, DEFAULT 0）, `generated_at`（DATETIME, NOT NULL）, `created_at`
- `stats_json` 包含：`period`, `date`, `time_range_start`, `time_range_end`, `total_alerts`, `risk_level`, `by_severity`, `top_exceptions`, `hourly_trend`, `by_view`
- 同一 `report_date` 的重复生成 SHALL upsert 覆盖旧记录，`regenerated_count += 1`，`generated_at` 更新

#### Scenario: First daily report generation
- **WHEN** 某日的日报首次生成
- **THEN** 系统 INSERT 新记录，`regenerated_count=0`

#### Scenario: Re-generate same day
- **WHEN** 同一日期再次触发生成
- **THEN** 系统 UPDATE 已有记录，`stats_json` 和 `insights_json` 覆盖，`regenerated_count` 递增，`generated_at` 更新为当前时间

### Requirement: Weekly report snapshot persistence
系统 SHALL 将周报统计快照持久化到 `weekly_reports` 表。

- `weekly_reports` 表字段：`id`, `week_start`（DATE，唯一，表示周一日期）, `stats_json`（TEXT, NOT NULL）, `generated_at`（DATETIME, NOT NULL）
- `stats_json` 包含：`period`, `week_start`, `week_end`, `total_alerts`, `daily_breakdown`（7 天数组）, `by_severity`, `top_exceptions`, `trend_vs_last_week`

#### Scenario: Weekly snapshot auto-generation
- **WHEN** 每周一凌晨 00:00 CST 触发周报生成
- **THEN** 系统计算前一周（周一~周日）聚合统计并 INSERT 到 `weekly_reports`

#### Scenario: Weekly report backfill from daily reports
- **WHEN** 某周已有完整的 7 天日报存档
- **THEN** 周报可直接聚合 7 条 `daily_reports.stats_json` 而无需重新查询事件表
