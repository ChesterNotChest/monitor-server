## Why

当前日报系统是实时计算+无持久化的一次性输出。AI（DeepSeek）参与度太浅——仅接收聚合数字（total/x次/最高频），产出的"洞察"与硬编码模板无异。需要让 AI 接触逐事件结构化数据、分步推理填表，并把结果持久化、定时自动生成、允许手动覆盖。

## What Changes

- **日报持久化**：新增 `daily_reports` 表，upsert by date。首次生成存盘，手动重新生成覆盖。
- **双层架构**：统计层（规则引擎，免费）涵盖告警数/分布/趋势；洞察层（DeepSeek AI）产结构化 JSON 的发现/预测/建议。
- **17:00 定时生成**：以北京时间 00:00~17:00 为当日范围，17:00 自动触发；次日凌晨补生成昨日 17:00~23:59 余量。
- **手动即时生成**：「现在生成当天日报」按钮，不管当前时刻直接拉取已有数据生成。可用于演示。
- **API Key 管理**：`.env` 存默认 key，前端可保存覆盖值，不再每次输入。
- **前端升级**：统计层直接展示图表（柱状/饼图）；洞察层展示 AI 文本+AI 产出的预测曲线、风险分布等数据图表。页面底部标注"北京时间 (UTC+8)"及"下次自动生成时间"。
- **周报增强**：每周一凌晨生成硬编码统计快照（无 AI），持久化 `weekly_reports` 表，聚合 7 天日报数据。
- **`stream-lifecycle` 清理**：`view_task.py` 移除未使用的 `start_merge` import，已在前置修复中完成。

## Capabilities

### New Capabilities
- `daily-report-persistence`: 日报持久化存储、upsert 覆盖、状态管理
- `report-scheduler`: 17:00 定时触发 + 次日凌晨补充余量 + 手动即时触发
- `api-key-management`: DeepSeek API Key 的 env 默认值 + 用户覆盖持久化
- `ai-structured-insights`: AI 分步推理产生结构化 JSON（预测数据、风险分布等，前端渲染图表）

### Modified Capabilities
- `report-api`: 新增日报 GET/POST（含持久化版本）、手动即时生成端点、周报快照端点；周报/月报增加持久化查询

## Impact

- **后端**：`report_task.py`（核心重构）、`report_router.py`（新端点）、新增 `daily_report` model/migration、`schedule_report.py`（定时任务）
- **前端**：日报展示页重构（统计层 + AI 洞察层双区域）、API key 设置表单、「立即生成」按钮、周报页面
- **配置**：`.env` / `.env.example` 新增 `DEEPSEEK_API_KEY`、`DEEPSEEK_REPORT_MODEL`
- **依赖**：已有 `httpx` + DeepSeek API，无新增外部依赖
