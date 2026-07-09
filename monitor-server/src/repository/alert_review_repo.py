"""告警审查 Repository。"""

from .base import BaseRepo
from ..models.alert_review import AlertReview


class AlertReviewRepo(BaseRepo[AlertReview]):
    """告警审查数据访问层。"""

    model = AlertReview
