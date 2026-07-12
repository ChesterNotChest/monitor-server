"""事件 Repository。"""

from datetime import datetime

from sqlalchemy import select

from src.models.situation_event import SituationEvent
from .base import BaseRepo


class SituationEventRepo(BaseRepo[SituationEvent]):
    model = SituationEvent

    def by_view(self, view_id: int) -> list[SituationEvent]:
        """按监控视图查询事件，按时间倒序。"""
        return list(
            self.db.scalars(
                select(SituationEvent)
                .where(SituationEvent.view_id == view_id)
                .order_by(SituationEvent.timestamp.desc())
            )
        )

    def by_time_range(
        self, start: datetime, end: datetime
    ) -> list[SituationEvent]:
        """按时间范围查询事件。"""
        return list(
            self.db.scalars(
                select(SituationEvent)
                .where(SituationEvent.timestamp.between(start, end))
                .order_by(SituationEvent.timestamp.desc())
            )
        )
