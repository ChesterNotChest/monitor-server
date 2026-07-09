"""录制记录 Repository。"""

from datetime import datetime

from sqlalchemy import select, func

from .base import BaseRepo
from ..models.recording import Recording


class RecordingRepo(BaseRepo[Recording]):
    model = Recording

    def by_view_time(
        self, view_id: int, start: datetime | None = None, end: datetime | None = None
    ) -> list[Recording]:
        """按 view_id 和时间范围查询录制记录。"""
        stmt = select(Recording).where(Recording.view_id == view_id)
        if start is not None:
            stmt = stmt.where(Recording.start_time >= start)
        if end is not None:
            stmt = stmt.where(Recording.end_time <= end)
        stmt = stmt.order_by(Recording.start_time.desc())
        return list(self.db.scalars(stmt))
