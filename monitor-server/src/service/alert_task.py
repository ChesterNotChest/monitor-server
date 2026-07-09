"""告警处理服务。"""

from sqlalchemy.orm import Session

from src.repository.situation_event_repo import SituationEventRepo
from src.repository.alert_review_repo import AlertReviewRepo


def list_alerts(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    """分页查询告警列表。"""
    repo = SituationEventRepo(db)
    items, total = repo.paginate(page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def mark_handled(db: Session, alert_id: int, user_id: int) -> bool:
    """标记告警为已处理。"""
    alert = SituationEventRepo(db).get(alert_id)
    if alert is None:
        return False
    AlertReviewRepo(db).create(
        alert_id=alert_id,
        reviewer_id=user_id,
        action="handled",
    )
    return True


def mark_false_alarm(db: Session, alert_id: int, user_id: int) -> bool:
    """标记告警为误报。"""
    alert = SituationEventRepo(db).get(alert_id)
    if alert is None:
        return False
    AlertReviewRepo(db).create(
        alert_id=alert_id,
        reviewer_id=user_id,
        action="false_alarm",
    )
    return True
