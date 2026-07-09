"""异常规则服务层门户。"""

from sqlalchemy.orm import Session

from src.models.exception import ExceptionDef
from src.repository.exception_def_repo import ExceptionDefRepo
from src.constants import SeverityLevel
from src.service.exception_module.binding import (
    bind_entity,
    unbind_entity,
    get_bound_entities,
    bind_action,
    unbind_action,
    get_bound_actions,
    bind_sound,
    unbind_sound,
    get_bound_sounds,
)


def _repo(db: Session) -> ExceptionDefRepo:
    return ExceptionDefRepo(db)


# ── CRUD ────────────────────────────────────────


def create_exception(
    db: Session, name: str, severity: SeverityLevel, group_id: int,
    face_result_id: int | None = None,
) -> ExceptionDef:
    return _repo(db).create(name=name, severity=severity, group_id=group_id, face_result_id=face_result_id)


def list_exceptions(
    db: Session, severity: SeverityLevel | None = None, page: int = 1, page_size: int = 20
) -> tuple[list[ExceptionDef], int]:
    repo = _repo(db)
    if severity is not None:
        items = repo.by_severity(severity)
        return items, len(items)
    return repo.paginate(page=page, page_size=page_size)


def get_exception(db: Session, id: int) -> ExceptionDef | None:
    return _repo(db).get(id)


def update_exception(
    db: Session, id: int,
    name: str | None = None,
    severity: SeverityLevel | None = None,
    group_id: int | None = None,
    face_result_id: int | None = None,
) -> ExceptionDef | None:
    return _repo(db).update(id, name=name, severity=severity, group_id=group_id, face_result_id=face_result_id)


def delete_exception(db: Session, id: int) -> bool:
    return _repo(db).delete(id)


# ── 导出绑定函数（API 直接引用）──────────────────

__all__ = [
    "create_exception",
    "list_exceptions",
    "get_exception",
    "update_exception",
    "delete_exception",
    "bind_entity",
    "unbind_entity",
    "get_bound_entities",
    "bind_action",
    "unbind_action",
    "get_bound_actions",
    "bind_sound",
    "unbind_sound",
    "get_bound_sounds",
]
