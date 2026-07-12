"""日志条目 Repository。"""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.log_entry import LogEntry


class LogEntryRepo(BaseRepo[LogEntry]):
    model = LogEntry

    def query(
        self,
        *,
        log_type: int | None = None,
        operator_id: int | None = None,
        view_id: int | None = None,
        event_id: int | None = None,
        severity: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[LogEntry], int]:
        """带多条件过滤的分页查询，按时间倒序。"""
        stmt = select(LogEntry).order_by(LogEntry.created_at.desc())

        if log_type is not None:
            stmt = stmt.where(LogEntry.log_type == log_type)
        if operator_id is not None:
            stmt = stmt.where(LogEntry.operator_id == operator_id)
        if view_id is not None:
            stmt = stmt.where(LogEntry.view_id == view_id)
        if event_id is not None:
            stmt = stmt.where(LogEntry.event_id == event_id)
        if severity is not None:
            stmt = stmt.where(LogEntry.severity == severity)
        if start is not None:
            stmt = stmt.where(LogEntry.created_at >= start)
        if end is not None:
            stmt = stmt.where(LogEntry.created_at <= end)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = list(self.db.scalars(stmt.offset(offset).limit(limit)))
        return items, total

    def stats_by_field(self, field: str) -> list[dict]:
        """按指定字段分组统计。field: 'log_type' | 'severity'"""
        col = getattr(LogEntry, field)
        stmt = (
            select(col, func.count(LogEntry.id).label("count"))
            .group_by(col)
            .order_by(func.count(LogEntry.id).desc())
        )
        rows = self.db.execute(stmt).all()
        return [{"value": row[0], "count": row[1]} for row in rows]
