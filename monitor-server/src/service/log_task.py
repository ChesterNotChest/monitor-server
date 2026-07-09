"""日志服务层 —— 写入入口 + 查询/统计。"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from src.repository.log_entry_repo import LogEntryRepo
from src.models.log_entry import LogEntry


class LogService:
    """统一日志写入入口。各 Service 模块在关键路径上调用。"""

    @staticmethod
    def write(
        db: Session,
        log_type: int,
        *,
        operator_id: int | None = None,
        view_id: int | None = None,
        event_id: int | None = None,
        severity: int | None = None,
        summary: str = "",
        details: dict | None = None,
    ) -> LogEntry:
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        return LogEntryRepo(db).create(
            log_type=log_type,
            operator_id=operator_id,
            view_id=view_id,
            event_id=event_id,
            severity=severity,
            summary=summary,
            details_json=details_json,
        )


def query_logs(
    db: Session,
    *,
    log_type: int | None = None,
    operator_id: int | None = None,
    view_id: int | None = None,
    event_id: int | None = None,
    severity: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LogEntry], int]:
    repo = LogEntryRepo(db)
    return repo.query(
        log_type=log_type,
        operator_id=operator_id,
        view_id=view_id,
        event_id=event_id,
        severity=severity,
        start=start,
        end=end,
        offset=(page - 1) * page_size,
        limit=page_size,
    )


def stats_by_log_type(db: Session) -> list[dict]:
    return LogEntryRepo(db).stats_by_field("log_type")


def stats_by_severity(db: Session) -> list[dict]:
    return LogEntryRepo(db).stats_by_field("severity")
