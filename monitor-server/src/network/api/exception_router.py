"""异常定义 API 路由 —— 负责人+运维员。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.exception_schema import ExceptionCreate, ExceptionResponse
from src.service import exception_task

router = APIRouter(prefix="/exceptions", tags=["异常定义"])
_perm = Depends(require_permission("exception:manage"))


@router.get("", response_model=list[ExceptionResponse])
def list_exceptions(db: Session = Depends(get_db), _user=_perm):
    return exception_task.list_exceptions(db)


@router.post("", response_model=ExceptionResponse, status_code=201)
def create_exception(body: ExceptionCreate, db: Session = Depends(get_db), _user=_perm):
    return exception_task.create_exception(db, **body.model_dump(exclude_none=True))


@router.put("/{exc_id}", response_model=ExceptionResponse)
def update_exception(exc_id: int, body: ExceptionCreate, db: Session = Depends(get_db), _user=_perm):
    r = exception_task.update_exception(db, exc_id, **body.model_dump(exclude_none=True))
    if r is None: raise HTTPException(404)
    return r


@router.delete("/{exc_id}", status_code=204)
def delete_exception(exc_id: int, db: Session = Depends(get_db), _user=_perm):
    if not exception_task.delete_exception(db, exc_id):
        raise HTTPException(404)
