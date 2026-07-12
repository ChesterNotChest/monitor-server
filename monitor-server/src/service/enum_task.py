"""枚举类型服务层门户 —— EntityType / ActionType / SoundType CRUD。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.entity_type import EntityType
from src.models.action_type import ActionType
from src.models.sound_type import SoundType
from src.repository.entity_type_repo import EntityTypeRepo
from src.repository.action_type_repo import ActionTypeRepo
from src.repository.sound_type_repo import SoundTypeRepo


class EnumNameConflictError(Exception):
    """枚举名称重复异常。"""

    pass


# ── helpers ─────────────────────────────────────


def _repo(db: Session, repo_cls):
    return repo_cls(db)


def _create(db, repo_cls, name: str):
    repo = _repo(db, repo_cls)
    try:
        return repo.create(name=name)
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"名称 '{name}' 已存在")


def _list_all(db, repo_cls) -> list:
    return _repo(db, repo_cls).all(limit=10_000)


def _update(db, repo_cls, id: int, name: str):
    repo = _repo(db, repo_cls)
    try:
        result = repo.update(id, name=name)
        if result is None:
            return None
        return result
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"名称 '{name}' 已存在")


def _delete(db, repo_cls, id: int) -> bool:
    return _repo(db, repo_cls).delete(id)


# ── EntityType ──────────────────────────────────


def create_entity(db: Session, name: str) -> EntityType:
    return _create(db, EntityTypeRepo, name)


def list_entities(db: Session) -> list[EntityType]:
    return _list_all(db, EntityTypeRepo)


def update_entity(db: Session, id: int, name: str) -> EntityType | None:
    return _update(db, EntityTypeRepo, id, name)


def delete_entity(db: Session, id: int) -> bool:
    return _delete(db, EntityTypeRepo, id)


# ── ActionType ──────────────────────────────────


def create_action(db: Session, name: str) -> ActionType:
    return _create(db, ActionTypeRepo, name)


def list_actions(db: Session) -> list[ActionType]:
    return _list_all(db, ActionTypeRepo)


def update_action(db: Session, id: int, name: str) -> ActionType | None:
    return _update(db, ActionTypeRepo, id, name)


def delete_action(db: Session, id: int) -> bool:
    return _delete(db, ActionTypeRepo, id)


# ── SoundType ───────────────────────────────────


def create_sound(db: Session, name: str) -> SoundType:
    return _create(db, SoundTypeRepo, name)


def list_sounds(db: Session) -> list[SoundType]:
    return _list_all(db, SoundTypeRepo)


def update_sound(db: Session, id: int, name: str) -> SoundType | None:
    return _update(db, SoundTypeRepo, id, name)


def delete_sound(db: Session, id: int) -> bool:
    return _delete(db, SoundTypeRepo, id)
