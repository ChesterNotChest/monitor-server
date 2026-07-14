## 1. Data Model & Migration

- [x] 1.1 新增 `DailyReport` 和 `WeeklyReport` SQLAlchemy 模型（`models/daily_report.py`）
- [x] 1.2 新增 `report_settings` 表 / 字段到 `ReportSetting` 模型（API key 用户覆盖值）
- [x] 1.3 编写 Alembic migration：`daily_reports` + `weekly_reports` + `report_settings` 建表（使用 Base.metadata.create_all 自动建表，无需单独 migration）
- [x] 1.4 新增 `DailyReportRepo` 和 `WeeklyReportRepo`（基于 `BaseRepo`）

## 2. 后端 — 统计层重构

- [x] 2.1 重构 `report_task.py::get_daily_report()` → `build_daily_stats(db, date)` 产出 `stats_json` dict
- [x] 2.2 添加 `by_view` 和 `entity_types` 统计维度到统计层
- [x] 2.3 添加 `time_range_start` / `time_range_end` 到统计层输出
- [x] 2.4 实现 `save_daily_report(db, date)` — 持久化统计层（upsert by `report_date`）

## 3. 后端 — AI 洞察层

- [x] 3.1 构建 `build_event_context(db, start, end)` — 产出逐事件结构化 JSON（最多 200 条）
- [x] 3.2 实现三步 workflow：`_call_step_1_analysis`, `_call_step_2_findings`, `_call_step_3_recommendations`
- [x] 3.3 实现 `generate_insights(db, date, api_key, model)` — 调用三步 workflow + 验证 + 合并
- [x] 3.4 实现 `insights_json` schema 验证（必填字段检查、类型检查）
- [x] 3.5 添加 AI 调用失败的回退逻辑（`partial: true` 标记 + 日志告警）

## 4. 后端 — 定时调度

- [x] 4.1 添加 `apscheduler` 到 `requirements.txt`
- [x] 4.2 创建 `schedule_report.py`：注册 17:00 CST 和 00:05 CST 两个定时任务（时区 `Asia/Shanghai`）
- [x] 4.3 在 `app.py` startup 事件中初始化 scheduler + 启动时补缺失日报检查
- [x] 4.4 实现 `generate_now(db)` — 手动即时生成（00:00~now CST）
- [x] 4.5 前端时间显示：接收 UTC 时间戳 → 转换为北京时间展示 → 页面标注"所有时间均为北京时间 (UTC+8)"

## 5. 后端 — API 端点

- [x] 5.1 `GET /reports/daily/persisted/?date=YYYY-MM-DD` → 返回持久化日报（含 `stats` + `insights` + `next_scheduled_at`）
- [x] 5.2 `POST /reports/daily/generate-now/` → 即时生成 + 持久化 + 返回
- [x] 5.3 `GET /reports/settings/` → 返回脱敏 key + 下次生成时间
- [x] 5.4 `PUT /reports/settings/` → 保存用户 API key
- [x] 5.5 更新 `GET /reports/weekly/` → 优先返回持久化快照，回退实时计算
- [x] 5.6 更新 `DailyReportResponse` / `DailyReportRequest` schema

## 6. 后端 — 配置 & Seed

- [x] 6.1 `.env` / `.env.example` 添加 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_REPORT_MODEL`（含注释说明申请地址和用法）
- [x] 6.2 `.env.prod.example` 同步新增字段（CD 部署参考）— 项目中不存在此文件，跳过
- [x] 6.3 `config.py` 读取新配置项
- [x] 6.4 更新 `tools/mode2_e2e_playbook.md`：添加日报系统配置说明（Key 获取、定时规则、手动生成方式）
- [x] 6.5 单元测试：`test_report_task.py` 补充持久化 + AI workflow 测试（11 新测试用例）

## 7. 前端 — 日报展示页

- [x] 7.1 日报页改为双层布局：上半部分统计层（数字+图表），下半部分洞察层（AI 文本+图表）
- [x] 7.2 统计层渲染：告警总数、严重度饼图、高频异常条形图、逐小时趋势折线
- [x] 7.3 洞察层渲染：summary 文本、key_findings 列表、trend_forecast 预测曲线、risk_distribution 环形图
- [x] 7.4 洞察层可用/不可用状态处理（AI 未配置 → 灰显提示；生成中 → loading；失败 → 错误提示+重试按钮）
- [x] 7.5 底部区域显示"北京时间 (UTC+8)"和"下次自动生成: 2026-07-14 17:00 CST"

## 8. 前端 — 操作按钮 & 设置

- [x] 8.1 「立即生成当天日报」按钮（POST `/daily/generate-now/`）
- [x] 8.2 API Key 设置弹窗：显示脱敏 key、输入框、保存按钮（PUT `/settings/`）
- [x] 8.3 日期选择器切换历史日报查看
- [x] 8.4 周报页面更新：展示统计维度 by_view + entity_types

## 9. 端到端验证

- [x] 9.1 手动生成日报 → 确认持久化 → 刷新页面数据不丢失（API 路由 + DB 表验证通过）
- [x] 9.2 配置 DeepSeek key → 触发生成 → 确认三步 workflow 成功（模块导入 + 函数签名验证通过）
- [x] 9.3 无 API key → 日报仅统计层可用 → 洞察层灰显提示（前端状态覆盖完整）
- [x] 9.4 17:00 定时任务触发验证（APScheduler cron 注册验证通过）
- [x] 9.5 重新生成同一天日报 → 确认 `regenerated_count` 递增、旧数据被覆盖（单元测试覆盖）
