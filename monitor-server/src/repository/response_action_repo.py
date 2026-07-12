"""响应动作 Repository。"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.response_action import ResponseAction
from .base import BaseRepo


class ResponseActionRepo(BaseRepo[ResponseAction]):
    model = ResponseAction

    def with_groups(self) -> list[ResponseAction]:
        """查询所有响应动作，并 eager load 其关联的告警分组。"""
        return list(
            self.db.scalars(
                select(ResponseAction)
                .options(selectinload(ResponseAction.alert_groups))
            )
        )
