"""异常定义管理服务。"""

from sqlalchemy.orm import Session

from src.repository.exception_def_repo import ExceptionDefRepo
from src.models.exception import exception_entities, exception_actions, exception_sounds


def list_exceptions(db: Session):
    return ExceptionDefRepo(db).with_details()


def create_exception(db: Session, **kwargs):
    entity_ids = kwargs.pop("entity_ids", [])
    action_ids = kwargs.pop("action_ids", [])
    sound_ids = kwargs.pop("sound_ids", [])
    r = ExceptionDefRepo(db).create(**kwargs)
    db.flush()  # 获取 r.id
    _set_m2m(db, r.id, entity_ids, action_ids, sound_ids)
    db.commit()
    return r


def update_exception(db: Session, exc_id: int, **kwargs):
    entity_ids = kwargs.pop("entity_ids", None)
    action_ids = kwargs.pop("action_ids", None)
    sound_ids = kwargs.pop("sound_ids", None)
    r = ExceptionDefRepo(db).update(exc_id, **kwargs)
    if entity_ids is not None or action_ids is not None or sound_ids is not None:
        # 清除旧关联 → 写入新关联
        db.execute(exception_entities.delete().where(exception_entities.c.exception_id == exc_id))
        db.execute(exception_actions.delete().where(exception_actions.c.exception_id == exc_id))
        db.execute(exception_sounds.delete().where(exception_sounds.c.exception_id == exc_id))
        repo = ExceptionDefRepo(db)
        exc = repo.get(exc_id)
        if exc:
            _set_m2m(db, exc_id,
                     entity_ids if entity_ids is not None else [e.id for e in exc.entities],
                     action_ids if action_ids is not None else [a.id for a in exc.actions],
                     sound_ids if sound_ids is not None else [s.id for s in exc.sounds])
    db.commit()
    return r


def delete_exception(db: Session, exc_id: int) -> bool:
    ok = ExceptionDefRepo(db).delete(exc_id)
    db.commit()
    return ok


def _set_m2m(db, exc_id, entity_ids, action_ids, sound_ids):
    if entity_ids:
        db.execute(exception_entities.insert(), [
            {"exception_id": exc_id, "entity_id": eid} for eid in entity_ids
        ])
    if action_ids:
        db.execute(exception_actions.insert(), [
            {"exception_id": exc_id, "action_id": aid} for aid in action_ids
        ])
    if sound_ids:
        db.execute(exception_sounds.insert(), [
            {"exception_id": exc_id, "sound_id": sid} for sid in sound_ids
        ])
