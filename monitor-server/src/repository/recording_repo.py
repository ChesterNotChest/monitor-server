"""录制记录 Repository。"""

from datetime import datetime

from sqlalchemy import text

from .base import BaseRepo
from ..models.recording import Recording


class RecordingRepo(BaseRepo[Recording]):
    model = Recording

    def create(self, **kwargs: object) -> Recording:
        """原生 SQL INSERT + SELECT 绕过 ORM mapper 配置。
        避免 partial import 时 ExceptionDef → FaceRecognitionResult
        字符串引用无法解析。"""
        self.db.execute(
            text("""
                INSERT INTO recordings (view_id, file_path, start_time, end_time)
                VALUES (:view_id, :file_path, :start_time, :end_time)
            """),
            {
                "view_id": kwargs["view_id"],
                "file_path": kwargs["file_path"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
            },
        )
        self.db.commit()

        row = self.db.execute(
            text("SELECT * FROM recordings WHERE id = last_insert_rowid()")
        )
        return Recording(**row.mappings().one())

    def by_view_time(
        self, view_id: int, start: datetime | None = None, end: datetime | None = None
    ) -> list[Recording]:
        """按 view_id 和时间范围查询录制记录。"""
        if start is not None and end is not None:
            row = self.db.execute(
                text("""
                    SELECT * FROM recordings
                    WHERE view_id = :view_id
                      AND start_time >= :start
                      AND end_time <= :end
                    ORDER BY start_time DESC
                """),
                {"view_id": view_id, "start": start, "end": end},
            )
        elif start is not None:
            row = self.db.execute(
                text("""
                    SELECT * FROM recordings
                    WHERE view_id = :view_id AND start_time >= :start
                    ORDER BY start_time DESC
                """),
                {"view_id": view_id, "start": start},
            )
        elif end is not None:
            row = self.db.execute(
                text("""
                    SELECT * FROM recordings
                    WHERE view_id = :view_id AND end_time <= :end
                    ORDER BY start_time DESC
                """),
                {"view_id": view_id, "end": end},
            )
        else:
            row = self.db.execute(
                text("""
                    SELECT * FROM recordings
                    WHERE view_id = :view_id
                    ORDER BY start_time DESC
                """),
                {"view_id": view_id},
            )
        return [Recording(**r) for r in row.mappings().all()]
