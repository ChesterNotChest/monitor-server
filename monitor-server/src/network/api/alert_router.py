"""告警 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.alert_schema import AlertListResponse, AlertResponse
from src.service import alert_service

router = APIRouter(prefix="/alerts", tags=["告警"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("alert:list")),
):
    """告警列表（分页）。"""
    return alert_service.list_alerts(db, page=page, page_size=page_size)


@router.put("/{alert_id}/handle")
def mark_handled(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("alert:handle")),
):
    """标记告警为已处理。"""
    if not alert_service.mark_handled(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"ok": True}


@router.put("/{alert_id}/false-alarm")
def mark_false_alarm(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("alert:handle")),
):
    """标记告警为误报。"""
    if not alert_service.mark_false_alarm(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"ok": True}
