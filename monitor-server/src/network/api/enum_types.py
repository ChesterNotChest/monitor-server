"""枚举类型 REST API 路由 —— EntityType / ActionType / SoundType。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.constants import API_PREFIX
from src.extensions import get_db
from src.schema.http.enum_types import EnumTypeCreate, EnumTypeUpdate, EnumTypeResponse
from src.service.enum_task import (
    EnumNameConflictError,
    create_entity,
    list_entities,
    update_entity,
    delete_entity,
    create_action,
    list_actions,
    update_action,
    delete_action,
    create_sound,
    list_sounds,
    update_sound,
    delete_sound,
)


def _to_response(obj) -> EnumTypeResponse:
    return EnumTypeResponse.model_validate(obj)


# ── EntityType ──────────────────────────────────

entity_router = APIRouter(prefix="/entity-types", tags=["枚举-实体类型"])


@entity_router.post("", response_model=EnumTypeResponse, status_code=201)
def create_entity_type(body: EnumTypeCreate, db: Session = Depends(get_db)):
    try:
        result = create_entity(db, name=body.name)
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@entity_router.get("", response_model=list[EnumTypeResponse])
def list_entity_types(db: Session = Depends(get_db)):
    return [_to_response(e) for e in list_entities(db)]


@entity_router.get("/{id}", response_model=EnumTypeResponse)
def get_entity_type(id: int, db: Session = Depends(get_db)):
    from src.repository.entity_type_repo import EntityTypeRepo
    obj = EntityTypeRepo(db).get(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="实体类型不存在")
    return _to_response(obj)
    pass


@entity_router.put("/{id}", response_model=EnumTypeResponse)
def update_entity_type(id: int, body: EnumTypeUpdate, db: Session = Depends(get_db)):
    try:
        result = update_entity(db, id, name=body.name)
        if result is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="实体类型不存在")
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@entity_router.delete("/{id}", status_code=204)
def delete_entity_type(id: int, db: Session = Depends(get_db)):
    if not delete_entity(db, id):
        raise HTTPException(status_code=404, detail="实体类型不存在")
    db.commit()


# ── ActionType ──────────────────────────────────

action_router = APIRouter(prefix="/action-types", tags=["枚举-行为类型"])


@action_router.post("", response_model=EnumTypeResponse, status_code=201)
def create_action_type(body: EnumTypeCreate, db: Session = Depends(get_db)):
    try:
        result = create_action(db, name=body.name)
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@action_router.get("", response_model=list[EnumTypeResponse])
def list_action_types(db: Session = Depends(get_db)):
    return [_to_response(a) for a in list_actions(db)]


@action_router.get("/{id}", response_model=EnumTypeResponse)
def get_action_type(id: int, db: Session = Depends(get_db)):
    # Simple lookup from repo
    from src.repository.action_type_repo import ActionTypeRepo
    obj = ActionTypeRepo(db).get(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="行为类型不存在")
    return _to_response(obj)


@action_router.put("/{id}", response_model=EnumTypeResponse)
def update_action_type(id: int, body: EnumTypeUpdate, db: Session = Depends(get_db)):
    try:
        result = update_action(db, id, name=body.name)
        if result is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="行为类型不存在")
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@action_router.delete("/{id}", status_code=204)
def delete_action_type(id: int, db: Session = Depends(get_db)):
    if not delete_action(db, id):
        raise HTTPException(status_code=404, detail="行为类型不存在")
    db.commit()


# ── SoundType ───────────────────────────────────

sound_router = APIRouter(prefix="/sound-types", tags=["枚举-声音类型"])


@sound_router.post("", response_model=EnumTypeResponse, status_code=201)
def create_sound_type(body: EnumTypeCreate, db: Session = Depends(get_db)):
    try:
        result = create_sound(db, name=body.name)
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@sound_router.get("", response_model=list[EnumTypeResponse])
def list_sound_types(db: Session = Depends(get_db)):
    return [_to_response(s) for s in list_sounds(db)]


@sound_router.get("/{id}", response_model=EnumTypeResponse)
def get_sound_type(id: int, db: Session = Depends(get_db)):
    from src.repository.sound_type_repo import SoundTypeRepo
    obj = SoundTypeRepo(db).get(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="声音类型不存在")
    return _to_response(obj)


@sound_router.put("/{id}", response_model=EnumTypeResponse)
def update_sound_type(id: int, body: EnumTypeUpdate, db: Session = Depends(get_db)):
    try:
        result = update_sound(db, id, name=body.name)
        if result is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="声音类型不存在")
        db.commit()
        return _to_response(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@sound_router.delete("/{id}", status_code=204)
def delete_sound_type(id: int, db: Session = Depends(get_db)):
    if not delete_sound(db, id):
        raise HTTPException(status_code=404, detail="声音类型不存在")
    db.commit()
