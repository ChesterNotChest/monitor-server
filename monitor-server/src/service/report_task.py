"""Report service for weekly, monthly, and AI-style daily summaries."""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json

import httpx
from sqlalchemy.orm import Session

from src.constants import SeverityLevel
from src.models.situation_event import SituationEvent
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.situation_event_repo import SituationEventRepo

_SEVERITY_LABELS = {1: "INFO", 2: "WARNING", 3: "CRITICAL", 4: "EMERGENCY"}
_DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
_DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"


class DeepSeekReportError(RuntimeError):
    """Raised when an external DeepSeek report generation call fails."""


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


def get_daily_report(db: Session, target_date: date | None = None) -> dict:
    """Generate a deterministic AI-style monitoring daily report.

    This uses local event statistics to produce summary text, findings, risk,
    and recommendations without requiring an external LLM service.
    """

    day = target_date or datetime.now().date()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    events = [
        event
        for event in SituationEventRepo(db).by_time_range(start, end)
        if start <= _naive(event.timestamp) < end
    ]

    severity_counter: Counter[str] = Counter()
    exception_counter: Counter[str] = Counter()
    hourly_counter: Counter[int] = Counter()
    for event in events:
        exc = _event_exception(db, event)
        severity_counter[_severity_name(getattr(exc, "severity", None))] += 1
        exception_counter[getattr(exc, "name", f"Exception #{event.exception_id}")] += 1
        hourly_counter[_naive(event.timestamp).hour] += 1

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
    risk_level = _risk_level(severity_counter, len(events))

    return {
        "period": "daily",
        "date": day.isoformat(),
        "total_alerts": len(events),
        "risk_level": risk_level,
        "summary": _summary(day, len(events), risk_level, top_exceptions),
        "key_findings": _findings(len(events), severity_counter, top_exceptions, hourly_trend),
        "recommendations": _recommendations(risk_level, top_exceptions),
        "by_severity": by_severity,
        "top_exceptions": top_exceptions,
        "hourly_trend": hourly_trend,
        "ai_provider": None,
        "ai_model": None,
        "ai_generated": False,
    }


def get_deepseek_daily_report(
    db: Session,
    api_key: str,
    target_date: date | None = None,
    model: str | None = None,
) -> dict:
    """Generate a daily report with DeepSeek using local statistics as context."""

    clean_key = api_key.strip()
    if not clean_key:
        raise DeepSeekReportError("DeepSeek API key is required")

    model_name = (model or _DEEPSEEK_DEFAULT_MODEL).strip() or _DEEPSEEK_DEFAULT_MODEL
    local_report = get_daily_report(db, target_date)
    ai_text = _call_deepseek_report_model(clean_key, model_name, local_report)

    return {
        **local_report,
        "summary": ai_text["summary"],
        "key_findings": ai_text["key_findings"],
        "recommendations": ai_text["recommendations"],
        "ai_provider": "deepseek",
        "ai_model": model_name,
        "ai_generated": True,
    }


def _call_deepseek_report_model(api_key: str, model: str, local_report: dict) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a monitoring operations analyst. "
                    "Return only valid JSON with keys summary, key_findings, recommendations. "
                    "summary must be one concise Chinese paragraph. "
                    "key_findings and recommendations must be Chinese string arrays with 1 to 5 items."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": "Generate a Chinese daily monitoring report from this structured context.",
                        "report_context": local_report,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
        "max_tokens": 900,
    }

    try:
        response = httpx.post(
            _DEEPSEEK_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise DeepSeekReportError(f"DeepSeek API returned HTTP {status}") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekReportError("DeepSeek report generation failed") from exc

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DeepSeekReportError("DeepSeek returned non-JSON report content") from exc

    return _validate_deepseek_report_text(parsed)


def _validate_deepseek_report_text(parsed: dict) -> dict:
    summary = parsed.get("summary")
    key_findings = parsed.get("key_findings")
    recommendations = parsed.get("recommendations")

    if not isinstance(summary, str) or not summary.strip():
        raise DeepSeekReportError("DeepSeek report is missing summary")
    if not _is_string_list(key_findings):
        raise DeepSeekReportError("DeepSeek report is missing key_findings")
    if not _is_string_list(recommendations):
        raise DeepSeekReportError("DeepSeek report is missing recommendations")

    return {
        "summary": summary.strip(),
        "key_findings": [item.strip() for item in key_findings if item.strip()],
        "recommendations": [item.strip() for item in recommendations if item.strip()],
    }


def _is_string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _event_exception(db: Session, event: SituationEvent):
    if event.exception is not None:
        return event.exception
    return ExceptionDefRepo(db).get(event.exception_id)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


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


def _summary(day: date, total: int, risk_level: str, top_exceptions: list[dict]) -> str:
    if total == 0:
        return f"{day.isoformat()} 未检测到告警事件，整体运行风险较低。"
    top = top_exceptions[0]["label"] if top_exceptions else "未分类异常"
    return (
        f"{day.isoformat()} 共检测到 {total} 起告警事件，"
        f"综合风险等级为 {risk_level}，高频异常为 {top}。"
    )


def _findings(
    total: int,
    severity_counter: Counter[str],
    top_exceptions: list[dict],
    hourly_trend: list[dict],
) -> list[str]:
    if total == 0:
        return ["当日无告警事件，未发现明显异常聚集。"]

    findings = [f"当日累计告警 {total} 起。"]
    high_count = severity_counter["EMERGENCY"] + severity_counter["CRITICAL"]
    if high_count:
        findings.append(f"高风险告警 {high_count} 起，需要优先复核。")
    if top_exceptions:
        findings.append(f"最频繁异常为 {top_exceptions[0]['label']}，出现 {top_exceptions[0]['value']} 次。")
    if hourly_trend:
        peak = max(hourly_trend, key=lambda item: item["count"])
        findings.append(f"告警峰值出现在 {peak['hour']}，该时段出现 {peak['count']} 起。")
    return findings


def _recommendations(risk_level: str, top_exceptions: list[dict]) -> list[str]:
    if risk_level == "LOW":
        return ["保持当前巡检策略，继续观察设备在线状态和告警趋势。"]

    recommendations = ["优先复核高风险告警对应的监控回放，并完成处置闭环。"]
    if top_exceptions:
        recommendations.append(f"针对 {top_exceptions[0]['label']} 增加规则核验和现场确认。")
    if risk_level in {"HIGH", "EMERGENCY"}:
        recommendations.append("建议负责人复盘当日告警高峰时段，必要时调整值守和通知策略。")
    return recommendations
