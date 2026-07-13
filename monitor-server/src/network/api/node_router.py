"""Node API 路由 —— 计算机节点与设备查询端点。

使用 Part A 的 Schema 模型（NodeResponse 等）做序列化。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http.common import OkResponse
from src.schema.http.device_schema import DeviceCreateRequest, DeviceCreateResponse
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


@router.post(
    "/{node_id}/devices/",
    response_model=DeviceCreateResponse,
    status_code=201,
    responses={
        400: {"description": "参数无效"},
        404: {"description": "Node 不存在"},
    },
)
def create_stream_device(
    node_id: int,
    request: DeviceCreateRequest,
    db: Session = Depends(get_db),
):
    """POST /api/v1/nodes/{node_id}/devices — 向虚拟 Node 注册自定义 RTMP 流设备。

    不验证流可达性——对方负责推送 RTMP 流到 SRS 服务。
    """
    if request.device_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="device_type 必须为 video 或 audio")

    result = node_task.create_stream_device(
        db,
        node_id=node_id,
        device_type=request.device_type,
        name=request.name,
        stream_url=request.stream_url,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Node 不存在")

    return result


@router.get(
    "/{node_id}/devices/",
    responses={404: {"description": "Node 不存在"}},
)
def list_stream_devices(node_id: int, db: Session = Depends(get_db)):
    """GET /api/v1/nodes/{node_id}/devices — 列出节点下所有设备（含 stream_url）。"""
    if node_task.get_node(db, node_id) is None:
        raise HTTPException(status_code=404, detail="Node 不存在")
    return node_task.list_stream_devices(db, node_id)


@router.delete(
    "/{node_id}/devices/{device_id}/",
    response_model=OkResponse,
    responses={404: {"description": "设备不存在"}},
)
def delete_stream_device(
    node_id: int,
    device_id: int,
    device_type: str = "video",
    db: Session = Depends(get_db),
):
    """DELETE /api/v1/nodes/{node_id}/devices/{device_id} — 删除自定义流设备。

    Query params:
        device_type: "video" 或 "audio"（默认 "video"）
    """
    if device_type not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="device_type 必须为 video 或 audio")

    ok = node_task.delete_stream_device(db, node_id, device_type, device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="设备不存在")
    return OkResponse()
