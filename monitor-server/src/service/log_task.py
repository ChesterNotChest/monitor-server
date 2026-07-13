"""系统日志服务 —— 读写结构化 LogEntry 记录。"""

import json

from sqlalchemy.orm import Session

from src.constants import LogType
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


def record_alert_event(db: Session, *, event, exception_def, recording_id: int | None = None):
    """记录告警触发日志，供 Web 日志中心展示。"""
    exception_name = getattr(exception_def, "name", None) or f"异常 #{event.exception_id}"
    severity = getattr(exception_def, "severity", None)
    severity_value = int(severity) if severity is not None else None
    severity_name = getattr(severity, "name", None)
    summary = f"告警触发：{exception_name}"[:256]
    details = {
        "action": "triggered",
        "event_id": event.id,
        "view_id": event.view_id,
        "exception_id": event.exception_id,
        "exception_name": exception_name,
        "severity": severity_name,
        "recording_id": recording_id,
    }

    return LogEntryRepo(db).create(
        log_type=int(LogType.ALERT),
        view_id=event.view_id,
        event_id=event.id,
        severity=severity_value,
        summary=summary,
        details_json=json.dumps(details, ensure_ascii=False),
    )

def record_operation(
    db: Session,
    *,
    operator_id: int | None,
    action: str,
    target_type: str,
    summary: str,
    target_id: str | int | None = None,
    details: dict | None = None,
):
    """记录用户操作日志，供 Web 日志中心展示。"""
    payload = {
        "action": action,
        "target_type": target_type,
    }
    if target_id is not None:
        payload["target_id"] = str(target_id)
    if details:
        payload.update(details)

    return LogEntryRepo(db).create(
        log_type=int(LogType.OPERATION),
        operator_id=operator_id,
        summary=summary[:256],
        details_json=json.dumps(payload, ensure_ascii=False),
    )

