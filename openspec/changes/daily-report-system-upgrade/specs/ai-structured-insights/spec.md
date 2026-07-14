## ADDED Requirements

### Requirement: Multi-step AI workflow
系统 SHALL 通过三步分阶段调用 DeepSeek API 生成结构化洞察，每步产出独立 JSON 片段。

- Step 1「模式分析」：输入逐事件 JSON 数组 + 按小时分布，AI 输出事件模式、聚类关系
- Step 2「趋势与发现」：基于 Step 1 输出 + 时序数据，AI 输出发现列表 + 预测型数据（`trend_forecast`）
- Step 3「建议与可视化」：基于前两步输出，AI 输出处置建议 + 图表数据（`risk_distribution`、`predictions`）

#### Scenario: Complete three-step workflow
- **WHEN** 日报触发 AI 洞察生成
- **THEN** 系统依次调用三步，收集全部 JSON 片段，合并为 `insights_json` 持久化

#### Scenario: Step 2 fails
- **WHEN** Step 2 的 DeepSeek API 调用失败（超时/额度不足/返回非 JSON）
- **THEN** 系统保留 Step 1 的输出，Step 3 和 Step 2 的 `trend_forecast` 设为 null，`insights_json` 标记 `{ "partial": true }`

### Requirement: Structured context for AI
系统 SHALL 向 AI 提供逐事件的结构化上下文，而非聚合数字。

上下文 JSON 包含：
- `report_meta`: `{ date, time_range, total_alerts, risk_level }`
- `events`: 逐事件数组，每项含 `{ time, view_name, exception_name, severity, face_result, fence_event, entity_types, action_types, sound_types, status, handled }`（最多 200 条，按时间倒序）
- `hourly_distribution`: `[{ hour: "08:00", count: 5, top_exception: "陌生人" }]`
- `by_view`: `[{ view_id, view_name, count }]`

#### Scenario: Events exceed 200 limit
- **WHEN** 当日告警超过 200 起
- **THEN** 系统取最新的 200 条 + 在 `report_meta` 中标注 `"truncated": true, "original_count": N`

### Requirement: AI output schema
AI 产出的 `insights_json` SHALL 遵循以下结构：

```json
{
  "partial": false,
  "summary": "一段中文概述",
  "key_findings": ["发现1", "发现2"],
  "pattern_analysis": { "clusters": [...], "correlations": [...] },
  "trend_forecast": {
    "periods": ["17:00", "18:00", ...],
    "predicted": [2, 3, 5, ...],
    "confidence": 0.7,
    "method": "based on hourly pattern similarity"
  },
  "risk_distribution": [
    { "label": "陌生人入侵", "value": 45, "severity": "WARNING" },
    { "label": "围栏靠近", "value": 28, "severity": "WARNING" }
  ],
  "recommendations": ["建议1", "建议2"],
  "generated_at": "2026-07-14T17:00:00+08:00"
}
```

#### Scenario: AI returns valid structured JSON
- **WHEN** DeepSeek 返回符合 schema 的 JSON
- **THEN** 系统验证必填字段后持久化到 `insights_json` 列

#### Scenario: AI returns invalid JSON
- **WHEN** DeepSeek 返回无法解析的 JSON 或缺少必填字段
- **THEN** 系统记录告警日志，`insights_json` 设为 null，前端洞察层显示"AI 生成失败"
