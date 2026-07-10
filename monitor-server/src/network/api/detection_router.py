"""检测枚举管理 API 路由 —— 负责人专有。

为简化路由注册，entity/action/sound 三种类型共用此模块，在 ``__init__.py`` 中分别添加前缀注册。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.detection_schema import DetectionTypeCreate, DetectionTypeResponse
from src.service import detection_task

_perm = Depends(require_permission("detection:manage"))


# ── Entity Types ──────────────────────────────

entity_router = APIRouter(prefix="/detection/entity-types", tags=["实体类型枚举"])

@entity_router.get("", response_model=list[DetectionTypeResponse])
def list_entities(db: Session = Depends(get_db), _user=_perm):
    return detection_task.list_entity_types(db)

@entity_router.post("", response_model=DetectionTypeResponse, status_code=201)
def create_entity(body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    return detection_task.create_entity_type(db, name=body.name)

@entity_router.put("/{item_id}", response_model=DetectionTypeResponse)
def update_entity(item_id: int, body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    r = detection_task.update_entity_type(db, item_id, name=body.name)
    if r is None: raise HTTPException(404)
    return r

@entity_router.delete("/{item_id}", status_code=204)
def delete_entity(item_id: int, db: Session = Depends(get_db), _user=_perm):
    if not detection_task.delete_entity_type(db, item_id):
        raise HTTPException(404)


# ── Action Types ──────────────────────────────

action_router = APIRouter(prefix="/detection/action-types", tags=["行为类型枚举"])

@action_router.get("", response_model=list[DetectionTypeResponse])
def list_actions(db: Session = Depends(get_db), _user=_perm):
    return detection_task.list_action_types(db)

@action_router.post("", response_model=DetectionTypeResponse, status_code=201)
def create_action(body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    return detection_task.create_action_type(db, name=body.name)

@action_router.put("/{item_id}", response_model=DetectionTypeResponse)
def update_action(item_id: int, body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    r = detection_task.update_action_type(db, item_id, name=body.name)
    if r is None: raise HTTPException(404)
    return r

@action_router.delete("/{item_id}", status_code=204)
def delete_action(item_id: int, db: Session = Depends(get_db), _user=_perm):
    if not detection_task.delete_action_type(db, item_id):
        raise HTTPException(404)


# ── Sound Types ───────────────────────────────

sound_router = APIRouter(prefix="/detection/sound-types", tags=["声音类型枚举"])

@sound_router.get("", response_model=list[DetectionTypeResponse])
def list_sounds(db: Session = Depends(get_db), _user=_perm):
    return detection_task.list_sound_types(db)

@sound_router.post("", response_model=DetectionTypeResponse, status_code=201)
def create_sound(body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    return detection_task.create_sound_type(db, name=body.name)

@sound_router.put("/{item_id}", response_model=DetectionTypeResponse)
def update_sound(item_id: int, body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    r = detection_task.update_sound_type(db, item_id, name=body.name)
    if r is None: raise HTTPException(404)
    return r

@sound_router.delete("/{item_id}", status_code=204)
def delete_sound(item_id: int, db: Session = Depends(get_db), _user=_perm):
    if not detection_task.delete_sound_type(db, item_id):
        raise HTTPException(404)


# ── Fence Event Types ──────────────────────────

fence_event_router = APIRouter(prefix="/detection/fence-event-types", tags=["围栏事件类型"])

from src.repository.fence_event_type_repo import FenceEventTypeRepo


@fence_event_router.get("", response_model=list[DetectionTypeResponse])
def list_fence_events(db: Session = Depends(get_db), _user=_perm):
    return FenceEventTypeRepo(db).all()


@fence_event_router.post("", response_model=DetectionTypeResponse, status_code=201)
def create_fence_event(body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    return FenceEventTypeRepo(db).create(name=body.name)


@fence_event_router.put("/{item_id}", response_model=DetectionTypeResponse)
def update_fence_event(item_id: int, body: DetectionTypeCreate, db: Session = Depends(get_db), _user=_perm):
    r = FenceEventTypeRepo(db).update(item_id, name=body.name)
    if r is None:
        raise HTTPException(404)
    return r


@fence_event_router.delete("/{item_id}", status_code=204)
def delete_fence_event(item_id: int, db: Session = Depends(get_db), _user=_perm):
    if not FenceEventTypeRepo(db).delete(item_id):
        raise HTTPException(404)
