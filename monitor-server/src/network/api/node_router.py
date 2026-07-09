"""Node API 路由 —— 计算机节点与设备查询端点。

使用 Part A 的 Schema 模型（NodeResponse 等）做序列化。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.service import node_task

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/")
def list_nodes(db: Session = Depends(get_db)):
    """GET /api/v1/nodes — 列出所有计算机节点。"""
    nodes = node_task.list_nodes(db)
    return {"nodes": nodes}


@router.get("/{node_id}/videos")
def list_videos(node_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/nodes/{node_id}/videos — 列出节点下的视频设备。"""
    videos = node_task.list_videos_by_node(db, node_id)
    return {"videos": videos}


@router.get("/{node_id}/audios")
def list_audios(node_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/nodes/{node_id}/audios — 列出节点下的音频设备。"""
    audios = node_task.list_audios_by_node(db, node_id)
    return {"audios": audios}
