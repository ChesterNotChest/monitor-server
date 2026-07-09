"""电子围栏 API 路由 —— 安全员专有。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.fence_schema import FenceCreate, FenceResponse
from src.service import fence_task

router = APIRouter(prefix="/fences", tags=["电子围栏"])


@router.get("", response_model=list[FenceResponse])
def list_fences(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    return fence_task.list_fences(db)


@router.post("", response_model=FenceResponse, status_code=201)
def create_fence(
    body: FenceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    return fence_task.create_fence(db, coords=body.coords)


@router.put("/{fence_id}", response_model=FenceResponse)
def update_fence(
    fence_id: int,
    body: FenceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    result = fence_task.update_fence(db, fence_id, coords=body.coords)
    if result is None:
        raise HTTPException(status_code=404, detail="围栏不存在")
    return result


@router.delete("/{fence_id}", status_code=204)
def delete_fence(
    fence_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    if not fence_task.delete_fence(db, fence_id):
        raise HTTPException(status_code=404, detail="围栏不存在")
