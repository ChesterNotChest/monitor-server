"""View API 路由 —— 监控视图 CRUD 端点。

使用 Part A 的 Schema 模型（ViewCreateRequest, ViewResponse 等）做请求/响应序列化。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http import ViewCreateRequest
from src.service import view_task

router = APIRouter(prefix="/views", tags=["views"])


@router.post("/")
def create_view(request: ViewCreateRequest, db: Session = Depends(get_db)):
    """POST /api/v1/views — 创建监控视图，启动 FFmpeg 合流。"""
    result = view_task.create_view(
        db,
        audio_id=request.audio_id,
        video_id=request.video_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return result


@router.get("/")
def list_views(db: Session = Depends(get_db)):
    """GET /api/v1/views — 列出所有监控视图。"""
    views = view_task.list_views(db)
    return {"views": views}


@router.get("/{view_id}")
def get_view(view_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/views/{view_id} — 获取单个视图详情。"""
    view = view_task.get_view(db, view_id)
    if view is None:
        raise HTTPException(status_code=404, detail="View not found")
    return view


@router.delete("/{view_id}")
def delete_view(view_id: int, db: Session = Depends(get_db)):
    """DELETE /api/v1/views/{view_id} — 删除视图，停止 FFmpeg 合流。"""
    ok = view_task.delete_view(db, view_id)
    if not ok:
        raise HTTPException(status_code=404, detail="View not found")
    return {"ok": True}
