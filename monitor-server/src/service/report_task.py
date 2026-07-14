"""Report service for weekly, monthly, and AI-style daily summaries.

升级要点：
  - build_daily_stats() 产出纯统计数据（stats_json），不含 AI 文本
  - get_daily_report() 向后兼容，委托 build_daily_stats() + 模板文本
  - save_daily_report() 持久化到 daily_reports 表（upsert by report_date）
  - 新增 by_view、entity_types 统计维度 + time_range_start/end
"""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json
import logging

import httpx
from sqlalchemy.orm import Session

from src.constants import SeverityLevel
from src.models.situation_event import SituationEvent
from src.repository.daily_report_repo import DailyReportRepo, WeeklyReportRepo, ReportSettingRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.situation_event_repo import SituationEventRepo

logger = logging.getLogger(__name__)

_SEVERITY_LABELS = {1: "INFO", 2: "WARNING", 3: "CRITICAL", 4: "EMERGENCY"}
_DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
_DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"

# Beijing timezone (UTC+8)
_CST = timezone(timedelta(hours=8))


class DeepSeekReportError(RuntimeError):
    """Raised when an external DeepSeek report generation call fails."""


# ── Timezone helpers ─────────────────────────────

def _cst_now() -> datetime:
    """Current time in Beijing timezone."""
    return datetime.now(_CST)


def _utc_to_cst(dt: datetime) -> datetime:
    """Convert UTC datetime to CST."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_CST)


def _cst_boundaries(report_date: date, time_start: time | None = None,
                    time_end: time | None = None) -> tuple[datetime, datetime]:
    """Return (start_utc, end_utc) for a CST date and optional time window."""
    start_cst = datetime.combine(report_date, time_start or time.min).replace(tzinfo=_CST)
    end_cst = datetime.combine(report_date, time_end or time.max).replace(tzinfo=_CST)
    return start_cst.astimezone(timezone.utc), end_cst.astimezone(timezone.utc)


def _cst_iso(dt: datetime) -> str:
    """Format datetime as ISO with +08:00 offset."""
    cst = _utc_to_cst(dt)
    return cst.isoformat()


# ── Stats layer (rule engine, always available) ──

def build_daily_stats(db: Session, report_date: date | None = None,
                      time_start: time | None = None,
                      time_end: time | None = None) -> dict:
    """Build stats_json dict from event data — pure statistics, no AI text.

    Args:
        db: database session
        report_date: CST date (default today)
        time_start: optional start time in CST (default 00:00)
        time_end: optional end time in CST (default 23:59:59.999999)

    Returns dict matching stats_json schema:
        period, date, time_range_start, time_range_end, total_alerts,
        risk_level, by_severity, top_exceptions, hourly_trend, by_view,
        entity_types
    """
    day = report_date or _cst_now().date()
    start_utc, end_utc = _cst_boundaries(day, time_start, time_end)

    events = [
        event
        for event in SituationEventRepo(db).by_time_range(start_utc, end_utc)
        if start_utc <= _naive_utc(event.timestamp) < end_utc
    ]

    severity_counter: Counter[str] = Counter()
    exception_counter: Counter[str] = Counter()
    hourly_counter: Counter[int] = Counter()
    view_counter: Counter[str] = Counter()
    entity_counter: Counter[str] = Counter()

    for event in events:
        exc = _event_exception(db, event)
        sev = _severity_name(getattr(exc, "severity", None))
        exc_name = getattr(exc, "name", f"Exception #{event.exception_id}")

        severity_counter[sev] += 1
        exception_counter[exc_name] += 1
        hourly_counter[_naive_utc(event.timestamp).hour] += 1

        # by_view
        if event.view_id:
            view_name = f"View {event.view_id}"
            if hasattr(event, "monitor_view") and event.monitor_view:
                view_name = getattr(event.monitor_view, "name", view_name)
            view_counter[view_name] += 1

        # entity_types from linked entities
        if exc and hasattr(exc, "entities") and exc.entities:
            for ent in exc.entities:
                entity_counter[getattr(ent, "name", f"Entity #{ent.id}")] += 1

    by_severity = [
        {"label": label, "value": severity_counter[label]}
        for label in ("INFO", "WARNING", "CRITICAL", "EMERGENCY")
        if severity_counter[label] > 0
    ]
    top_exceptions = [
        {"label": name, "value": count}
        for name, count in exception_counter.most_common(5)
    ]
    hourly_trend = [
        {"hour": f"{hour:02d}:00", "count": hourly_counter[hour]}
        for hour in range(24)
        if hourly_counter[hour] > 0
    ]
    by_view = [
        {"label": name, "value": count}
        for name, count in view_counter.most_common(10)
    ]
    entity_types = [
        {"label": name, "value": count}
        for name, count in entity_counter.most_common(10)
    ]
    risk_level = _risk_level(severity_counter, len(events))

    return {
        "period": "daily",
        "date": day.isoformat(),
        "time_range_start": _cst_iso(start_utc),
        "time_range_end": _cst_iso(end_utc),
        "total_alerts": len(events),
        "risk_level": risk_level,
        "by_severity": by_severity,
        "top_exceptions": top_exceptions,
        "hourly_trend": hourly_trend,
        "by_view": by_view,
        "entity_types": entity_types,
    }


def save_daily_report(db: Session, report_date: date, stats_json: dict,
                      insights_json: dict | None = None,
                      ai_provider: str | None = None,
                      ai_model: str | None = None) -> dict:
    """Persist daily report to daily_reports table (upsert by report_date).

    Returns the persisted DailyReport as dict.
    """
    repo = DailyReportRepo(db)
    report = repo.upsert(
        report_date=report_date,
        stats_json=json.dumps(stats_json, ensure_ascii=False),
        insights_json=json.dumps(insights_json, ensure_ascii=False) if insights_json else None,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )
    db.commit()
    return {
        "report_date": report.report_date.isoformat(),
        "stats_json": json.loads(report.stats_json) if isinstance(report.stats_json, str) else report.stats_json,
        "insights_json": json.loads(report.insights_json) if report.insights_json else None,
        "ai_provider": report.ai_provider,
        "ai_model": report.ai_model,
        "regenerated_count": report.regenerated_count,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


def load_daily_report(db: Session, report_date: date) -> dict | None:
    """Load persisted daily report by date. Returns None if not found."""
    from src.models.daily_report import DailyReport
    from sqlalchemy import select as _sel

    row = db.scalar(_sel(DailyReport).where(DailyReport.report_date == report_date))
    if not row:
        return None

    return {
        "report_date": row.report_date.isoformat(),
        "stats": json.loads(row.stats_json) if isinstance(row.stats_json, str) else row.stats_json,
        "insights": json.loads(row.insights_json) if row.insights_json else None,
        "ai_provider": row.ai_provider,
        "ai_model": row.ai_model,
        "regenerated_count": row.regenerated_count,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


# ── Legacy daily report (backward compat) ────────

def get_daily_report(db: Session, target_date: date | None = None) -> dict:
    """Generate a deterministic AI-style monitoring daily report.

    Delegates to build_daily_stats() for stats, adds template text for
    backward compatibility with the existing API response shape.
    """
    stats = build_daily_stats(db, target_date)

    day = target_date or _cst_now().date()
    total = stats["total_alerts"]
    risk = stats["risk_level"]
    top_exc = stats["top_exceptions"]
    hourly = stats["hourly_trend"]

    return {
        **stats,
        "summary": _summary_text(day, total, risk, top_exc),
        "key_findings": _findings_text(total, stats["by_severity"], top_exc, hourly),
        "recommendations": _recommendations_text(risk, top_exc),
        "ai_provider": None,
        "ai_model": None,
        "ai_generated": False,
    }


def _summary_text(day: date, total: int, risk: str, top_exc: list[dict]) -> str:
    if total == 0:
        return f"{day.isoformat()} 未检测到告警事件，整体运行风险较低。"
    top = top_exc[0]["label"] if top_exc else "未分类异常"
    return (
        f"{day.isoformat()} 共检测到 {total} 起告警事件，"
        f"综合风险等级为 {risk}，高频异常为 {top}。"
    )


def _findings_text(total: int, by_sev: list[dict],
                   top_exc: list[dict], hourly: list[dict]) -> list[str]:
    if total == 0:
        return ["当日无告警事件，未发现明显异常聚集。"]
    findings = [f"当日累计告警 {total} 起。"]
    sev_map = {s["label"]: s["value"] for s in by_sev}
    high_count = sev_map.get("EMERGENCY", 0) + sev_map.get("CRITICAL", 0)
    if high_count:
        findings.append(f"高风险告警 {high_count} 起，需要优先复核。")
    if top_exc:
        findings.append(f"最频繁异常为 {top_exc[0]['label']}，出现 {top_exc[0]['value']} 次。")
    if hourly:
        peak = max(hourly, key=lambda item: item["count"])
        findings.append(f"告警峰值出现在 {peak['hour']}，该时段出现 {peak['count']} 起。")
    return findings


def _recommendations_text(risk: str, top_exc: list[dict]) -> list[str]:
    if risk == "LOW":
        return ["保持当前巡检策略，继续观察设备在线状态和告警趋势。"]
    recs = ["优先复核高风险告警对应的监控回放，并完成处置闭环。"]
    if top_exc:
        recs.append(f"针对 {top_exc[0]['label']} 增加规则核验和现场确认。")
    if risk in {"HIGH", "EMERGENCY"}:
        recs.append("建议负责人复盘当日告警高峰时段，必要时调整值守和通知策略。")
    return recs


# ── Weekly / Monthly ─────────────────────────────

def _get_report(db: Session, days: int, label: str) -> dict:
    """Shared weekly/monthly aggregate report."""
    event_repo = SituationEventRepo(db)
    exc_repo = ExceptionDefRepo(db)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    all_events = event_repo.all(limit=1000)
    period_events = [event for event in all_events if event.timestamp and _aware(event.timestamp) >= since]

    severity_counter: Counter[str] = Counter()
    exc_counter: Counter[str] = Counter()
    for event in period_events:
        if event.exception_id:
            exc = exc_repo.get(event.exception_id)
            if exc:
                severity_counter[_severity_name(exc.severity)] += 1
                exc_counter[exc.name] += 1

    return {
        "period": label,
        "total_alerts": len(period_events),
        "by_severity": [
            {"label": severity, "value": count}
            for severity, count in sorted(severity_counter.items())
        ],
        "top_exceptions": [
            {"label": name, "value": count}
            for name, count in exc_counter.most_common(10)
        ],
    }


def get_weekly_report(db: Session) -> dict:
    """Current weekly report."""
    return _get_report(db, 7, "weekly")


def get_monthly_report(db: Session) -> dict:
    """Current monthly report."""
    return _get_report(db, 30, "monthly")


# ── AI Insight layer (DeepSeek 3-step workflow) ──

# Max events sent to AI for context
_MAX_EVENT_CONTEXT = 200


def build_event_context(db: Session, report_date: date,
                        time_start: time | None = None,
                        time_end: time | None = None) -> dict:
    """Build per-event structured JSON context for AI analysis.

    Returns dict with: report_meta, events (max 200), hourly_distribution, by_view
    """
    day = report_date
    start_utc, end_utc = _cst_boundaries(day, time_start, time_end)

    events_raw = [
        event
        for event in SituationEventRepo(db).by_time_range(start_utc, end_utc)
        if start_utc <= _naive_utc(event.timestamp) < end_utc
    ]

    truncated = len(events_raw) > _MAX_EVENT_CONTEXT
    events_raw = events_raw[-_MAX_EVENT_CONTEXT:]  # newest 200

    events_json = []
    hourly_dist: Counter[int] = Counter()
    view_dist: Counter[str] = Counter()

    for event in events_raw:
        exc = _event_exception(db, event)
        ev_dict = {
            "time": _cst_iso(event.timestamp),
            "view_id": event.view_id,
            "exception_name": getattr(exc, "name", f"Exception #{event.exception_id}") if exc else f"Exception #{event.exception_id}",
            "severity": _severity_name(getattr(exc, "severity", None)) if exc else "UNKNOWN",
            "face_result": getattr(event, "face_result_id", None),
            "fence_event": getattr(event, "fence_event_id", None),
            "entity_types": [getattr(e, "name", str(e.id)) for e in exc.entities] if exc and hasattr(exc, "entities") and exc.entities else [],
            "action_types": [getattr(a, "name", str(a.id)) for a in exc.actions] if exc and hasattr(exc, "actions") and exc.actions else [],
            "sound_types": [getattr(s, "name", str(s.id)) for s in exc.sounds] if exc and hasattr(exc, "sounds") and exc.sounds else [],
            "status": getattr(event, "status", "created"),
        }
        events_json.append(ev_dict)
        hourly_dist[_naive_utc(event.timestamp).hour] += 1
        view_name = f"View {event.view_id}"
        if hasattr(event, "monitor_view") and event.monitor_view:
            view_name = getattr(event.monitor_view, "name", view_name)
        view_dist[view_name] += 1

    return {
        "report_meta": {
            "date": day.isoformat(),
            "time_range": f"{_cst_iso(start_utc)} ~ {_cst_iso(end_utc)}",
            "total_alerts": len(events_raw),
            "truncated": truncated,
            "original_count": len(events_raw) + (_MAX_EVENT_CONTEXT if truncated else 0),
        },
        "events": events_json,
        "hourly_distribution": [
            {"hour": f"{h:02d}:00", "count": hourly_dist[h]}
            for h in range(24) if hourly_dist[h] > 0
        ],
        "by_view": [
            {"view_name": name, "count": count}
            for name, count in view_dist.most_common(10)
        ],
    }


async def generate_insights(db: Session, report_date: date,
                            api_key: str, model: str | None = None) -> dict:
    """Run the 3-step AI workflow to produce insights_json.

    Args:
        db: database session
        report_date: CST date
        api_key: DeepSeek API key
        model: model name (default from settings or deepseek-v4-flash)

    Returns insights_json dict (spec schema), or None on total failure.
    Sets partial=True if any step fails.
    """
    model_name = (model or _DEEPSEEK_DEFAULT_MODEL).strip() or _DEEPSEEK_DEFAULT_MODEL

    # Build context once
    ctx = build_event_context(db, report_date)
    stats = build_daily_stats(db, report_date)

    partial = False
    step1_out = None
    step2_out = None
    step3_out = None

    # Step 1: Pattern Analysis
    try:
        step1_out = await _call_step_1_analysis(api_key, model_name, ctx, stats)
        logger.info("Step 1 (pattern analysis) completed")
    except Exception as e:
        logger.warning("Step 1 failed: %s", e)
        partial = True

    # Step 2: Trends & Findings (depends on step 1)
    if step1_out:
        try:
            step2_out = await _call_step_2_findings(api_key, model_name, ctx, stats, step1_out)
            logger.info("Step 2 (trends & findings) completed")
        except Exception as e:
            logger.warning("Step 2 failed: %s", e)
            partial = True

    # Step 3: Recommendations & Visualization (depends on steps 1+2)
    if step1_out and step2_out:
        try:
            step3_out = await _call_step_3_recommendations(api_key, model_name, ctx, stats,
                                                           step1_out, step2_out)
            logger.info("Step 3 (recommendations) completed")
        except Exception as e:
            logger.warning("Step 3 failed: %s", e)
            partial = True

    # Merge results into insights_json
    insights = _merge_insights(stats, step1_out, step2_out, step3_out, partial)
    return insights


def _merge_insights(stats: dict, step1: dict | None, step2: dict | None,
                    step3: dict | None, partial: bool) -> dict:
    """Merge step outputs into the standardized insights_json shape."""
    return {
        "partial": partial or (step1 is None),
        "summary": (step1 or {}).get("summary", "AI 洞察生成失败，仅统计层可用。"),
        "key_findings": (step2 or {}).get("key_findings",
                                           [(step1 or {}).get("summary", "无\n发现")][:1]),
        "pattern_analysis": (step1 or {}).get("pattern_analysis"),
        "trend_forecast": (step2 or {}).get("trend_forecast"),
        "risk_distribution": (step3 or {}).get("risk_distribution",
                                                stats.get("by_severity", [])),
        "recommendations": (step3 or {}).get("recommendations",
                                              ["AI 服务不可用，请根据统计层数据人工判断。"]),
        "generated_at": _cst_now().isoformat(),
    }


# ── Step prompts ─────────────────────────────────

async def _call_step_1_analysis(api_key: str, model: str, ctx: dict, stats: dict) -> dict:
    """Step 1: Pattern Analysis — identify event patterns and clusters."""
    system_prompt = (
        "你是一个监控运营分析师。根据提供的事件数据进行模式分析。\n"
        "返回严格的 JSON 对象，包含以下键：\n"
        "- summary: 一段中文概述（100-200字），总结当日监控态势。\n"
        "- pattern_analysis: 对象，含 clusters（事件聚类列表）和 correlations（关联发现列表，可为空数组）。\n"
        "每个 cluster/correlation 为 { \"description\": \"...\", \"events_count\": N, \"severity\": \"...\" }\n\n"
        "【重要规则】\n"
        "1. 所有分析必须严格来源于提供的数据，禁止编造、推测、或使用训练数据中的通用知识。\n"
        "2. 如果提供的事件数据为空（total_alerts=0 或 events_sample=[]）：\n"
        "   - summary 必须明确写「当日无告警事件，数据不足以进行分析」\n"
        "   - clusters 和 correlations 必须为空数组 []\n"
        "3. 如果数据量极少（total_alerts < 5）：必须在 summary 中注明「数据量不足，以下分析仅供参考」\n"
        "4. 每个发现必须能追溯到输入数据中的具体数字，不要凭空添加数字。"
    )
    user_prompt = json.dumps({
        "task": "Step 1: 对以下监控事件数据进行模式分析",
        "stats": {k: stats[k] for k in ("total_alerts", "risk_level", "by_severity",
                                         "top_exceptions", "hourly_trend")},
        "hourly_distribution": ctx.get("hourly_distribution", []),
        "by_view": ctx.get("by_view", []),
        "events_sample": ctx.get("events", [])[:50],
    }, ensure_ascii=False)

    return await _call_deepseek(api_key, model, system_prompt, user_prompt)


async def _call_step_2_findings(api_key: str, model: str, ctx: dict, stats: dict,
                                step1: dict) -> dict:
    """Step 2: Trends & Findings — discover trends and produce forecast data."""
    system_prompt = (
        "你是一个监控数据分析师。基于第一步的模式分析结果和时间序列数据，发现趋势并生成预测。\n"
        "返回严格的 JSON 对象，包含以下键：\n"
        "- key_findings: 字符串数组（3-5条中文发现）\n"
        "- trend_forecast: 对象，含 periods（字符串数组）、predicted（数字数组）、"
        "confidence（0-1之间的数字）、method（字符串，简述预测方法）\n\n"
        "【重要规则】\n"
        "1. 所有发现和预测必须严格来源于提供的数据，禁止编造趋势或凭空构造预测数值。\n"
        "2. 如果没有小时级趋势数据（hourly_trend 或 hourly_distribution 为空）：\n"
        "   - trend_forecast.periods 和 trend_forecast.predicted 必须为空数组 []\n"
        "   - confidence 必须设为 0\n"
        "   - method 必须写「数据不足以进行预测」\n"
        "3. 如果有数据但数据点较少（< 6 个小时有数据）：\n"
        "   - confidence 必须 <= 0.3\n"
        "   - method 中注明「基于有限数据点」\n"
        "4. predicted 数组中的每个值必须能从输入数据的趋势中合理解释，不得出现与历史趋势矛盾的大幅波动。\n"
        "5. key_findings 中的每条发现必须引用具体的输入数据（如时段、数量），不得泛泛而谈。"
    )
    user_prompt = json.dumps({
        "task": "Step 2: 基于模式分析和时序数据进行趋势发现与预测",
        "pattern_analysis": step1.get("pattern_analysis"),
        "hourly_trend": stats.get("hourly_trend", []),
        "hourly_distribution": ctx.get("hourly_distribution", []),
        "by_view": ctx.get("by_view", []),
    }, ensure_ascii=False)

    return await _call_deepseek(api_key, model, system_prompt, user_prompt)


async def _call_step_3_recommendations(api_key: str, model: str, ctx: dict, stats: dict,
                                       step1: dict, step2: dict) -> dict:
    """Step 3: Recommendations & Visualization data."""
    system_prompt = (
        "你是一个安防运营顾问。基于前两步的分析结果，提供处置建议和图表数据。\n"
        "返回严格的 JSON 对象，包含以下键：\n"
        "- recommendations: 字符串数组（3-5条中文建议）\n"
        "- risk_distribution: 对象数组，每项含 label（字符串）、value（数字）、"
        "severity（字符串，INFO/WARNING/CRITICAL/EMERGENCY 之一）\n\n"
        "【重要规则】\n"
        "1. 所有建议必须基于输入数据中的实际告警情况，禁止给出与数据无关的通用建议。\n"
        "2. risk_distribution 必须使用输入数据中 by_severity 或 top_exceptions 的实际数字，"
        "严禁编造不存在的风险项或凭空填入数字。\n"
        "3. 如果 input data 中所有 by_severity 的 value 都为 0 或为空：\n"
        "   - risk_distribution 必须为空数组 []\n"
        "   - recommendations 第一条必须是「当日无告警，无需特殊处置」\n"
        "4. 如果预警级别为 LOW：recommendations 应以日常维护和持续观察为主，不要夸大风险。\n"
        "5. 每条 recommendation 必须对应输入数据中的具体发现，每项 risk_distribution 的 value 必须能在 "
        "by_severity 或 top_exceptions 中找到来源。"
    )
    user_prompt = json.dumps({
        "task": "Step 3: 提供处置建议和风险分布数据",
        "summary": step1.get("summary", ""),
        "key_findings": step2.get("key_findings", []),
        "trend_forecast": step2.get("trend_forecast"),
        "by_severity": stats.get("by_severity", []),
        "top_exceptions": stats.get("top_exceptions", []),
        "risk_level": stats.get("risk_level"),
    }, ensure_ascii=False)

    return await _call_deepseek(api_key, model, system_prompt, user_prompt)


async def _call_deepseek(api_key: str, model: str,
                         system_prompt: str, user_prompt: str, timeout: float = 60.0) -> dict:
    """Call DeepSeek API and return parsed JSON response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            _DEEPSEEK_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    parsed = json.loads(content)
    return parsed


# ── Insights schema validation ───────────────────

def validate_insights_json(insights: dict) -> dict:
    """Validate insights_json structure. Returns the dict or raises ValueError."""
    if not isinstance(insights, dict):
        raise ValueError("insights_json must be a dict")

    # Required top-level keys
    for key in ("summary", "key_findings", "recommendations"):
        if key not in insights:
            raise ValueError(f"insights_json missing required key: {key}")

    if not isinstance(insights["summary"], str):
        raise ValueError("insights_json.summary must be a string")
    if not _is_string_list(insights["key_findings"]):
        raise ValueError("insights_json.key_findings must be a string array")
    if not _is_string_list(insights["recommendations"]):
        raise ValueError("insights_json.recommendations must be a string array")

    return insights


# ── Legacy DeepSeek (backward compat, single-call) ──

def get_deepseek_daily_report(
    db: Session,
    api_key: str,
    target_date: date | None = None,
    model: str | None = None,
) -> dict:
    """Legacy single-call DeepSeek report — backward compat for POST /daily/deepseek/.

    Uses the new build_daily_stats() but old single-prompt AI call.
    """
    clean_key = api_key.strip()
    if not clean_key:
        raise DeepSeekReportError("DeepSeek API key is required")

    model_name = (model or _DEEPSEEK_DEFAULT_MODEL).strip() or _DEEPSEEK_DEFAULT_MODEL

    import asyncio
    stats = build_daily_stats(db, target_date)

    # Sync bridge: run the old single-call style
    ctx = build_event_context(db, target_date or _cst_now().date())
    merged = asyncio.run(_legacy_single_call(clean_key, model_name, stats, ctx))
    return {
        **stats,
        "summary": merged.get("summary", ""),
        "key_findings": merged.get("key_findings", []),
        "recommendations": merged.get("recommendations", []),
        "ai_provider": "deepseek",
        "ai_model": model_name,
        "ai_generated": True,
    }


async def _legacy_single_call(api_key: str, model: str, stats: dict, ctx: dict) -> dict:
    """Old-style single prompt (for legacy endpoint compat)."""
    system_prompt = (
        "You are a monitoring operations analyst. "
        "Return only valid JSON with keys summary, key_findings, recommendations. "
        "summary must be one concise Chinese paragraph. "
        "key_findings and recommendations must be Chinese string arrays with 1 to 5 items."
    )
    user_prompt = json.dumps({
        "task": "Generate a Chinese daily monitoring report from this structured context.",
        "stats": {k: stats[k] for k in ("total_alerts", "risk_level", "by_severity",
                                         "top_exceptions", "hourly_trend")},
        "by_view": ctx.get("by_view", []),
    }, ensure_ascii=False)
    result = await _call_deepseek(api_key, model, system_prompt, user_prompt)
    return result


def _is_string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


# ── Helpers ──────────────────────────────────────

def _event_exception(db: Session, event: SituationEvent):
    if event.exception is not None:
        return event.exception
    return ExceptionDefRepo(db).get(event.exception_id)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _naive_utc(value: datetime) -> datetime:
    """Ensure datetime is UTC-aware for comparison with _cst_boundaries outputs."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _severity_name(value) -> str:
    if isinstance(value, SeverityLevel):
        return value.name
    if isinstance(value, int):
        return _SEVERITY_LABELS.get(value, str(value))
    if hasattr(value, "name"):
        return str(value.name)
    return str(value or "UNKNOWN")


def _risk_level(severity_counter: Counter[str], total: int) -> str:
    if severity_counter["EMERGENCY"] > 0:
        return "EMERGENCY"
    if severity_counter["CRITICAL"] > 0 or total >= 10:
        return "HIGH"
    if severity_counter["WARNING"] > 0 or total >= 3:
        return "MEDIUM"
    return "LOW"
