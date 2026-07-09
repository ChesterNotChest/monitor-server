"""设备管理 API 路由 —— 运维员专有。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.device_schema import NodeHealthResponse
from src.service import device_task

router = APIRouter(prefix="/devices", tags=["设备管理"])


@router.get("/nodes")
def list_nodes(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("device:list")),
):
    """列出所有 Node。"""
    return device_task.list_nodes(db)


@router.get("/nodes/{node_id}/health", response_model=NodeHealthResponse)
def node_health(
    node_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("device:health")),
):
    """Node 健康状态。"""
    result = device_task.get_node_health(db, node_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Node 不存在")
    return result


@router.post("/nodes/{node_id}/onboard")
def onboard(
    node_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("device:onboard")),
):
    """设备接入。"""
    if not device_task.onboard_device(db, node_id):
        raise HTTPException(status_code=404, detail="Node 不存在")
    return {"ok": True}
