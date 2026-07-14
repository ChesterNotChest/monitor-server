## ADDED Requirements

### Requirement: 17:00 CST daily report auto-generation
系统 SHALL 在每日北京时间 17:00 自动生成当日日报（时间范围：当日 00:00~17:00 CST）。

- 使用 APScheduler 或类似定时任务框架注册 Cron 任务：`0 17 * * *`（Asia/Shanghai 时区）
- 统计层（`stats_json`）SHALL 在此步完成计算和持久化
- 若配置了 DeepSeek API Key，洞察层（`insights_json`）SHALL 在统计层完成后异步调用生成

#### Scenario: Normal 17:00 trigger
- **WHEN** 北京时间 17:00 到达
- **THEN** 系统生成当日 00:00~17:00 CST 范围的日报并持久化

#### Scenario: Server was down at 17:00
- **WHEN** 服务在 17:00 不可用，随后恢复
- **THEN** 系统在下次启动时检查当日日报是否缺失，若缺失则立即补生成

### Requirement: Midnight remainder supplement
系统 SHALL 在次日凌晨 00:05 CST 补生成前一日 17:00~23:59 CST 范围的余量日报。

- 补生成逻辑：读取前一日 17:00 的主日报，将时间范围扩展至 00:00~23:59，重新计算统计层数据，覆盖原记录
- `stats_json.time_range_end` 更新为 `23:59`

#### Scenario: Supplement merges remainder
- **WHEN** 凌晨 00:05 触发补充
- **THEN** 前一日日报的 `stats_json` 更新为全天数据，`time_range_end` 变为 `23:59`

#### Scenario: Supplement on missing primary report
- **WHEN** 前一日 17:00 的日报因服务不可用而缺失
- **THEN** 凌晨补充时应生成完整的 00:00~23:59 全天日报

### Requirement: Manual instant generation
系统 SHALL 提供「立即生成当天日报」按钮，无论当前时刻，拉取从当天 00:00 CST 到当前时刻的所有数据生成日报。

- `POST /api/v1/reports/daily/generate-now/` 端点
- 生成逻辑与统计层相同，但时间范围为 `00:00~now`

#### Scenario: Mid-day manual trigger
- **WHEN** 用户在 14:30 CST 点击「立即生成」
- **THEN** 系统生成 00:00~14:30 范围的日报数据并持久化

#### Scenario: After-hours manual trigger
- **WHEN** 用户在 20:00 CST 点击「立即生成」
- **THEN** 系统生成当日 00:00~20:00 范围的日报数据并持久化；后续 17:00 定时或凌晨补充时覆盖为更完整数据
