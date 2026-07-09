"""异常规则 M2M 绑定管理 —— 管理 ExceptionDef ↔ EntityType/ActionType/SoundType 关联。"""

from sqlalchemy.orm import Session

from src.models.exception import ExceptionDef
from src.models.entity_type import EntityType
from src.models.action_type import ActionType
from src.models.sound_type import SoundType
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.entity_type_repo import EntityTypeRepo
from src.repository.action_type_repo import ActionTypeRepo
from src.repository.sound_type_repo import SoundTypeRepo


def _get_exception(db: Session, exception_id: int) -> ExceptionDef | None:
    return ExceptionDefRepo(db).get(exception_id)


# ── EntityType ──────────────────────────────────


def bind_entity(db: Session, exception_id: int, entity_id: int) -> list[EntityType] | None:
    """绑定实体类型（幂等）。返回当前 entities 列表；异常不存在返回 None。"""
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None

    already = any(e.id == entity_id for e in exc.entities)
    if not already:
        entity = EntityTypeRepo(db).get(entity_id)
        if entity is not None:
            exc.entities.append(entity)
            db.flush()

    db.refresh(exc)
    return list(exc.entities)


def unbind_entity(db: Session, exception_id: int, entity_id: int) -> bool:
    """解绑实体类型（幂等）。返回 True 表示异常存在。"""
    exc = _get_exception(db, exception_id)
    if exc is None:
        return False

    exc.entities = [e for e in exc.entities if e.id != entity_id]
    db.flush()
    return True


def get_bound_entities(db: Session, exception_id: int) -> list[EntityType] | None:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None
    return list(exc.entities)


# ── ActionType ──────────────────────────────────


def bind_action(db: Session, exception_id: int, action_id: int) -> list[ActionType] | None:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None

    already = any(a.id == action_id for a in exc.actions)
    if not already:
        action = ActionTypeRepo(db).get(action_id)
        if action is not None:
            exc.actions.append(action)
            db.flush()

    db.refresh(exc)
    return list(exc.actions)


def unbind_action(db: Session, exception_id: int, action_id: int) -> bool:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return False

    exc.actions = [a for a in exc.actions if a.id != action_id]
    db.flush()
    return True


def get_bound_actions(db: Session, exception_id: int) -> list[ActionType] | None:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None
    return list(exc.actions)


# ── SoundType ───────────────────────────────────


def bind_sound(db: Session, exception_id: int, sound_id: int) -> list[SoundType] | None:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None

    already = any(s.id == sound_id for s in exc.sounds)
    if not already:
        sound = SoundTypeRepo(db).get(sound_id)
        if sound is not None:
            exc.sounds.append(sound)
            db.flush()

    db.refresh(exc)
    return list(exc.sounds)


def unbind_sound(db: Session, exception_id: int, sound_id: int) -> bool:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return False

    exc.sounds = [s for s in exc.sounds if s.id != sound_id]
    db.flush()
    return True


def get_bound_sounds(db: Session, exception_id: int) -> list[SoundType] | None:
    exc = _get_exception(db, exception_id)
    if exc is None:
        return None
    return list(exc.sounds)
