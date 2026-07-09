"""告警分级 API 路由 —— 负责人+运维员。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.alert_group_schema import AlertGroupCreate, AlertGroupResponse
from src.service import alert_group_task

router = APIRouter(prefix="/alert-groups", tags=["告警分级"])
_perm = Depends(require_permission("alert_group:manage"))


@router.get("", response_model=list[AlertGroupResponse])
def list_groups(db: Session = Depends(get_db), _user=_perm):
    return alert_group_task.list_alert_groups(db)


@router.post("", response_model=AlertGroupResponse, status_code=201)
def create_group(body: AlertGroupCreate, db: Session = Depends(get_db), _user=_perm):
    return alert_group_task.create_alert_group(db, name=body.name)


@router.put("/{group_id}", response_model=AlertGroupResponse)
def update_group(group_id: int, body: AlertGroupCreate, db: Session = Depends(get_db), _user=_perm):
    r = alert_group_task.update_alert_group(db, group_id, name=body.name)
    if r is None: raise HTTPException(404)
    return r


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db), _user=_perm):
    if not alert_group_task.delete_alert_group(db, group_id):
        raise HTTPException(404)
