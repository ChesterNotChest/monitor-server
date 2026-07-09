"""检测枚举管理服务 —— 实体类型/行为类型/声音类型 CRUD。"""

from sqlalchemy.orm import Session

from src.repository.entity_type_repo import EntityTypeRepo
from src.repository.action_type_repo import ActionTypeRepo
from src.repository.sound_type_repo import SoundTypeRepo


def _crud(repo_class, db: Session, action: str, *, item_id: int = None, name: str = None):
    """通用 CRUD 包装。"""
    repo = repo_class(db)
    if action == "list":
        return repo.all()
    elif action == "create":
        return repo.create(name=name)
    elif action == "update":
        return repo.update(item_id, name=name)
    elif action == "delete":
        return repo.delete(item_id)


# ── Entity Types ──────────────────────────────

def list_entity_types(db: Session):
    return _crud(EntityTypeRepo, db, "list")

def create_entity_type(db: Session, name: str):
    return _crud(EntityTypeRepo, db, "create", name=name)

def update_entity_type(db: Session, item_id: int, name: str):
    return _crud(EntityTypeRepo, db, "update", item_id=item_id, name=name)

def delete_entity_type(db: Session, item_id: int):
    return _crud(EntityTypeRepo, db, "delete", item_id=item_id)


# ── Action Types ──────────────────────────────

def list_action_types(db: Session):
    return _crud(ActionTypeRepo, db, "list")

def create_action_type(db: Session, name: str):
    return _crud(ActionTypeRepo, db, "create", name=name)

def update_action_type(db: Session, item_id: int, name: str):
    return _crud(ActionTypeRepo, db, "update", item_id=item_id, name=name)

def delete_action_type(db: Session, item_id: int):
    return _crud(ActionTypeRepo, db, "delete", item_id=item_id)


# ── Sound Types ──────────────────────────────

def list_sound_types(db: Session):
    return _crud(SoundTypeRepo, db, "list")

def create_sound_type(db: Session, name: str):
    return _crud(SoundTypeRepo, db, "create", name=name)

def update_sound_type(db: Session, item_id: int, name: str):
    return _crud(SoundTypeRepo, db, "update", item_id=item_id, name=name)

def delete_sound_type(db: Session, item_id: int):
    return _crud(SoundTypeRepo, db, "delete", item_id=item_id)
