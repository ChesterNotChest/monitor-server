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
    """列出所有电子围栏。

    **权限**: fence:manage
    """
    return fence_task.list_fences(db)


@router.post(
    "",
    response_model=FenceResponse,
    status_code=201,
    responses={404: {"description": "关联监控视图不存在"}, 422: {"description": "请求体校验失败"}},
)
def create_fence(
    body: FenceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    """创建电子围栏。

    **权限**: fence:manage
    """
    return fence_task.create_fence(
        db,
        name=body.name,
        view_id=body.view_id,
        coords=body.coords,
        dwell_time=body.dwell_time,
        density=body.density,
        leave_frames=body.leave_frames,
    )


@router.put(
    "/{fence_id}",
    response_model=FenceResponse,
    responses={404: {"description": "围栏不存在"}},
)
def update_fence(
    fence_id: int,
    body: FenceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    """更新电子围栏。

    **权限**: fence:manage
    """
    result = fence_task.update_fence(db, fence_id, coords=body.coords)
    if result is None:
        raise HTTPException(status_code=404, detail="围栏不存在")
    return result


@router.delete(
    "/{fence_id}",
    status_code=204,
    responses={404: {"description": "围栏不存在"}},
)
def delete_fence(
    fence_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("fence:manage")),
):
    """删除电子围栏。

    **权限**: fence:manage
    """
    if not fence_task.delete_fence(db, fence_id):
        raise HTTPException(status_code=404, detail="围栏不存在")
