"""报表服务 —— 周报/月报聚合。"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.repository.situation_event_repo import SituationEventRepo
from src.repository.exception_def_repo import ExceptionDefRepo

_SEVERITY_LABELS = {1: "INFO", 2: "WARNING", 3: "CRITICAL", 4: "EMERGENCY"}


def _get_report(db: Session, days: int, label: str) -> dict:
    """通用报表聚合。"""
    event_repo = SituationEventRepo(db)
    exc_repo = ExceptionDefRepo(db)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    all_events = event_repo.all(limit=1000)
    period_events = [e for e in all_events if e.timestamp and e.timestamp >= since]

    # 按严重级别聚合
    severity_counter: Counter = Counter()
    exc_counter: Counter = Counter()
    for e in period_events:
        if e.exception_id:
            exc = exc_repo.get(e.exception_id)
            if exc:
                sev_key = _SEVERITY_LABELS.get(exc.severity, str(exc.severity))
                severity_counter[sev_key] += 1
                exc_counter[exc.name] += 1

    by_severity = [
        {"label": sev, "value": count}
        for sev, count in sorted(severity_counter.items())
    ]

    top_exceptions = [
        {"label": name, "value": count}
        for name, count in exc_counter.most_common(10)
    ]

    return {
        "period": label,
        "total_alerts": len(period_events),
        "by_severity": by_severity,
        "top_exceptions": top_exceptions,
    }


def get_weekly_report(db: Session) -> dict:
    """本周报告。"""
    return _get_report(db, 7, "weekly")


def get_monthly_report(db: Session) -> dict:
    """本月报告。"""
    return _get_report(db, 30, "monthly")
