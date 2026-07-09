"""异常规则 REST API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.constants import API_PREFIX, DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SeverityLevel
from src.extensions import get_db
from src.schema.http.exception import (
    ExceptionCreate,
    ExceptionUpdate,
    ExceptionResponse,
    ExceptionListResponse,
    EntityBindRequest,
    ActionBindRequest,
    SoundBindRequest,
)
from src.service.exception_task import (
    create_exception,
    list_exceptions,
    get_exception,
    update_exception,
    delete_exception,
    bind_entity,
    unbind_entity,
    bind_action,
    unbind_action,
    bind_sound,
    unbind_sound,
)

router = APIRouter(prefix="/exceptions", tags=["异常规则"])


def _to_response(obj) -> ExceptionResponse:
    return ExceptionResponse.model_validate(obj)


# ── CRUD ────────────────────────────────────────


@router.post("", response_model=ExceptionResponse, status_code=201)
def create(body: ExceptionCreate, db: Session = Depends(get_db)):
    result = create_exception(db, severity=body.severity, group_id=body.group_id)
    db.commit()
    return _to_response(result)


@router.get("", response_model=ExceptionListResponse)
def list_all(
    db: Session = Depends(get_db),
    severity: SeverityLevel | None = Query(None),
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = list_exceptions(db, severity=severity, page=page, page_size=page_size)
    return ExceptionListResponse(
        items=[_to_response(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{id}", response_model=ExceptionResponse)
def get_one(id: int, db: Session = Depends(get_db)):
    obj = get_exception(db, id)
    if obj is None:
        raise HTTPException(status_code=404, detail="异常规则不存在")
    return _to_response(obj)


@router.put("/{id}", response_model=ExceptionResponse)
def update(id: int, body: ExceptionUpdate, db: Session = Depends(get_db)):
    result = update_exception(db, id, severity=body.severity, group_id=body.group_id)
    if result is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()
    return _to_response(result)


@router.delete("/{id}", status_code=204)
def delete(id: int, db: Session = Depends(get_db)):
    if not delete_exception(db, id):
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()


# ── 绑定 EntityType ─────────────────────────────


@router.post("/{id}/entities")
def bind_entity_type(id: int, body: EntityBindRequest, db: Session = Depends(get_db)):
    result = bind_entity(db, exception_id=id, entity_id=body.entity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()
    return {"entities": [{"id": e.id, "name": e.name} for e in result]}


@router.delete("/{id}/entities/{entity_id}", status_code=204)
def unbind_entity_type(id: int, entity_id: int, db: Session = Depends(get_db)):
    if not unbind_entity(db, exception_id=id, entity_id=entity_id):
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()


# ── 绑定 ActionType ─────────────────────────────


@router.post("/{id}/actions")
def bind_action_type(id: int, body: ActionBindRequest, db: Session = Depends(get_db)):
    result = bind_action(db, exception_id=id, action_id=body.action_id)
    if result is None:
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()
    return {"actions": [{"id": a.id, "name": a.name} for a in result]}


@router.delete("/{id}/actions/{action_id}", status_code=204)
def unbind_action_type(id: int, action_id: int, db: Session = Depends(get_db)):
    if not unbind_action(db, exception_id=id, action_id=action_id):
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()


# ── 绑定 SoundType ──────────────────────────────


@router.post("/{id}/sounds")
def bind_sound_type(id: int, body: SoundBindRequest, db: Session = Depends(get_db)):
    result = bind_sound(db, exception_id=id, sound_id=body.sound_id)
    if result is None:
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()
    return {"sounds": [{"id": s.id, "name": s.name} for s in result]}


@router.delete("/{id}/sounds/{sound_id}", status_code=204)
def unbind_sound_type(id: int, sound_id: int, db: Session = Depends(get_db)):
    if not unbind_sound(db, exception_id=id, sound_id=sound_id):
        raise HTTPException(status_code=404, detail="异常规则不存在")
    db.commit()
