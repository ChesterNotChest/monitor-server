"""告警处理服务。"""

import asyncio
import logging

from sqlalchemy.orm import Session

from src.repository.situation_event_repo import SituationEventRepo
from src.repository.alert_review_repo import AlertReviewRepo

logger = logging.getLogger(__name__)


def list_alerts(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    """分页查询告警列表。"""
    repo = SituationEventRepo(db)
    items, total = repo.paginate(page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def acknowledge_alert(db: Session, alert_id: int, user_id: int) -> bool:
    """确认告警 —— 创建 AlertReview 并取消上报计时器。"""
    from src.service.alert_module.escalation import STATUS_ACKNOWLEDGED, acknowledge
    from src.repository.user_repo import UserRepo

    alert = SituationEventRepo(db).get(alert_id)
    if alert is None:
        return False

    user = UserRepo(db).get(user_id)
    if user is None:
        return False

    # 创建确认记录
    AlertReviewRepo(db).create(
        alert_id=alert_id,
        reviewer_id=user_id,
        action="acknowledged",
    )

    # 更新状态
    alert.status = STATUS_ACKNOWLEDGED
    db.commit()

    # 取消计时器（异步）
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(acknowledge(alert_id, user))
    except RuntimeError:
        asyncio.run(acknowledge(alert_id, user))

    return True


def mark_handled(db: Session, alert_id: int, user_id: int) -> bool:
    """标记告警为已处理。"""
    from src.service.alert_module.escalation import STATUS_HANDLED

    alert = SituationEventRepo(db).get(alert_id)
    if alert is None:
        return False
    AlertReviewRepo(db).create(
        alert_id=alert_id,
        reviewer_id=user_id,
        action="handled",
    )
    alert.status = STATUS_HANDLED
    db.commit()
    return True


def mark_false_alarm(db: Session, alert_id: int, user_id: int) -> bool:
    """标记告警为误报。"""
    from src.service.alert_module.escalation import STATUS_FALSE_ALARM

    alert = SituationEventRepo(db).get(alert_id)
    if alert is None:
        return False
    AlertReviewRepo(db).create(
        alert_id=alert_id,
        reviewer_id=user_id,
        action="false_alarm",
    )
    alert.status = STATUS_FALSE_ALARM
    db.commit()
    return True
