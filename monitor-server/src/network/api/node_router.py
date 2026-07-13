"""Node API 路由 —— 计算机节点与设备查询端点。

使用 Part A 的 Schema 模型（NodeResponse 等）做序列化。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http.node_schema import (
    NodeListResponse,
    VideoDeviceListResponse,
    AudioDeviceListResponse,
)
from src.service import node_task

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/", response_model=NodeListResponse)
def list_nodes(db: Session = Depends(get_db)):
    """GET /api/v1/nodes — 列出所有计算机节点。"""
    nodes = node_task.list_nodes(db)
    return NodeListResponse(nodes=nodes)


@router.get(
    "/{node_id}/videos/",
    response_model=VideoDeviceListResponse,
    responses={404: {"description": "Node 不存在"}},
)
def list_videos(node_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/nodes/{node_id}/videos — 列出节点下的视频设备。"""
    videos = node_task.list_videos_by_node(db, node_id)
    return VideoDeviceListResponse(videos=videos)


@router.get(
    "/{node_id}/audios/",
    response_model=AudioDeviceListResponse,
    responses={404: {"description": "Node 不存在"}},
)
def list_audios(node_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/nodes/{node_id}/audios — 列出节点下的音频设备。"""
    audios = node_task.list_audios_by_node(db, node_id)
    return AudioDeviceListResponse(audios=audios)
