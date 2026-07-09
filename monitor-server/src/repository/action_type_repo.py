"""行为类型（SlowFast）Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.action_type import ActionType


class ActionTypeRepo(BaseRepo[ActionType]):
    """SlowFast 行为类型枚举数据访问层。"""

    model = ActionType

    def __init__(self, db: Session) -> None:
        super().__init__(db)
