"""报表服务 —— 周报/月报聚合。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.repository.situation_event_repo import SituationEventRepo


def _get_report(db: Session, days: int, label: str) -> dict:
    """通用报表聚合。"""
    repo = SituationEventRepo(db)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # 统计周期内的告警
    all_events = repo.all(limit=1000)
    period_events = [e for e in all_events if e.timestamp and e.timestamp >= since]

    return {
        "period": label,
        "total_alerts": len(period_events),
        "by_severity": [],
        "top_exceptions": [],
    }


def get_weekly_report(db: Session) -> dict:
    """本周报告。"""
    return _get_report(db, 7, "weekly")


def get_monthly_report(db: Session) -> dict:
    """本月报告。"""
    return _get_report(db, 30, "monthly")
