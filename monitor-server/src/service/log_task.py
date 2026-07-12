"""系统日志服务 —— 从数据库读取 LogEntry 记录。"""

from sqlalchemy.orm import Session

from src.repository.log_entry_repo import LogEntryRepo


def list_logs(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    """日志分页列表。"""
    repo = LogEntryRepo(db)
    items, total = repo.query(
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_log(db: Session, log_id: int) -> dict | None:
    """按 ID 查询单条日志。"""
    repo = LogEntryRepo(db)
    return repo.get(log_id)
