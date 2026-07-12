"""告警分组 Repository。"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.alert_group import AlertGroup
from .base import BaseRepo


class AlertGroupRepo(BaseRepo[AlertGroup]):
    model = AlertGroup

    def with_responses(self) -> list[AlertGroup]:
        """查询所有告警分组，并 eager load 其关联的响应动作。"""
        return list(
            self.db.scalars(
                select(AlertGroup)
                .options(selectinload(AlertGroup.responses))
            )
        )
