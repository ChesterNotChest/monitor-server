"""告警分组与响应动作 REST API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.constants import API_PREFIX
from src.extensions import get_db
from src.schema.http.alert import (
    ResponseActionCreate,
    ResponseActionUpdate,
    ResponseActionResponse,
    AlertGroupCreate,
    AlertGroupUpdate,
    AlertGroupResponse,
    ResponseBindRequest,
)
from src.service.alert_task import (
    create_response,
    list_responses,
    update_response,
    delete_response,
    create_group,
    list_groups,
    get_group,
    update_group,
    delete_group,
    bind_response,
    unbind_response,
    get_group_responses,
)
from src.service.enum_task import EnumNameConflictError


def _resp_action(obj) -> ResponseActionResponse:
    return ResponseActionResponse.model_validate(obj)


def _resp_group(obj) -> AlertGroupResponse:
    return AlertGroupResponse.model_validate(obj)


# ── ResponseAction（独立路由）───────────────────

response_router = APIRouter(prefix="/response-actions", tags=["告警-响应动作"])


@response_router.post("", response_model=ResponseActionResponse, status_code=201)
def create_response_action(body: ResponseActionCreate, db: Session = Depends(get_db)):
    try:
        result = create_response(db, name=body.name)
        db.commit()
        return _resp_action(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@response_router.get("", response_model=list[ResponseActionResponse])
def list_response_actions(db: Session = Depends(get_db)):
    return [_resp_action(r) for r in list_responses(db)]


@response_router.get("/{id}", response_model=ResponseActionResponse)
def get_response_action(id: int, db: Session = Depends(get_db)):
    from src.repository.response_action_repo import ResponseActionRepo
    obj = ResponseActionRepo(db).get(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="响应动作不存在")
    return _resp_action(obj)


@response_router.put("/{id}", response_model=ResponseActionResponse)
def update_response_action(id: int, body: ResponseActionUpdate, db: Session = Depends(get_db)):
    try:
        result = update_response(db, id, name=body.name)
        if result is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="响应动作不存在")
        db.commit()
        return _resp_action(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@response_router.delete("/{id}", status_code=204)
def delete_response_action(id: int, db: Session = Depends(get_db)):
    if not delete_response(db, id):
        raise HTTPException(status_code=404, detail="响应动作不存在")
    db.commit()


# ── AlertGroup（独立 CRUD + 嵌套绑定）────────────

group_router = APIRouter(prefix="/alert-groups", tags=["告警-告警分组"])


@group_router.post("", response_model=AlertGroupResponse, status_code=201)
def create_alert_group(body: AlertGroupCreate, db: Session = Depends(get_db)):
    try:
        result = create_group(db, name=body.name)
        db.commit()
        return _resp_group(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@group_router.get("", response_model=list[AlertGroupResponse])
def list_alert_groups(db: Session = Depends(get_db)):
    items, _ = list_groups(db, page_size=100)
    return [_resp_group(g) for g in items]


@group_router.get("/{id}", response_model=AlertGroupResponse)
def get_alert_group(id: int, db: Session = Depends(get_db)):
    obj = get_group(db, id)
    if obj is None:
        raise HTTPException(status_code=404, detail="告警分组不存在")
    return _resp_group(obj)


@group_router.put("/{id}", response_model=AlertGroupResponse)
def update_alert_group(id: int, body: AlertGroupUpdate, db: Session = Depends(get_db)):
    try:
        result = update_group(db, id, name=body.name)
        if result is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="告警分组不存在")
        db.commit()
        return _resp_group(result)
    except EnumNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@group_router.delete("/{id}", status_code=204)
def delete_alert_group(id: int, db: Session = Depends(get_db)):
    if not delete_group(db, id):
        raise HTTPException(status_code=404, detail="告警分组不存在")
    db.commit()


# ── 嵌套路由：绑定/解绑响应动作 ─────────────────

@group_router.post("/{id}/responses", response_model=list[ResponseActionResponse])
def bind_response_to_group(
    id: int, body: ResponseBindRequest, db: Session = Depends(get_db)
):
    result = bind_response(db, group_id=id, response_id=body.response_id)
    if result is None:
        raise HTTPException(status_code=404, detail="告警分组不存在")
    db.commit()
    return [_resp_action(r) for r in result]


@group_router.delete("/{id}/responses/{response_id}", status_code=204)
def unbind_response_from_group(id: int, response_id: int, db: Session = Depends(get_db)):
    if not unbind_response(db, group_id=id, response_id=response_id):
        raise HTTPException(status_code=404, detail="告警分组不存在")
    db.commit()
