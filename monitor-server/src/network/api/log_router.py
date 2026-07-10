"""系统日志 API 路由 —— 运维员专有。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.log_schema import LogEntry, LogListResponse
from src.service import log_task

router = APIRouter(prefix="/logs", tags=["系统日志"])
_perm = Depends(require_permission("log:view"))


@router.get("", response_model=LogListResponse)
def list_logs(
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    _user=_perm,
):
    """系统日志分页列表。

    **权限**: log:view
    """
    return log_task.list_logs(db, page=page, page_size=page_size)


@router.get(
    "/{log_id}",
    response_model=LogEntry,
    responses={404: {"description": "日志不存在"}},
)
def get_log(log_id: int, db: Session = Depends(get_db), _user=_perm):
    """按 ID 查询日志详情。

    **权限**: log:view
    """
    entry = log_task.get_log(db, log_id)
    if entry is None:
        raise HTTPException(404)
    return entry
