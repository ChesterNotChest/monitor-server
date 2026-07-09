"""响应动作内部逻辑 —— ResponseAction CRUD。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.response_action import ResponseAction
from src.repository.response_action_repo import ResponseActionRepo
from src.service.enum_task import EnumNameConflictError


def _repo(db: Session) -> ResponseActionRepo:
    return ResponseActionRepo(db)


def create_response(db: Session, name: str) -> ResponseAction:
    try:
        return _repo(db).create(name=name)
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"响应动作 '{name}' 已存在")


def list_responses(db: Session) -> list[ResponseAction]:
    return _repo(db).with_groups()


def update_response(db: Session, id: int, name: str) -> ResponseAction | None:
    repo = _repo(db)
    try:
        return repo.update(id, name=name)
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"响应动作 '{name}' 已存在")


def delete_response(db: Session, id: int) -> bool:
    return _repo(db).delete(id)
