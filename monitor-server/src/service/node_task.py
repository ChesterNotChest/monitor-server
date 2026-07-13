"""Node Task 门户 —— 节点与设备只读查询的轻量包装。

Router 不直接调 Repository，统一通过此模块访问，保持分层一致性。
"""

import logging

from sqlalchemy.orm import Session

from src.config import settings
from src.constants import VIRTUAL_NODE_TOKEN
from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo

logger = logging.getLogger(__name__)


def list_nodes(db: Session):
    """列出所有计算机节点，虚拟 Node 标记 is_virtual=True。"""
    nodes = NodeRepo(db).all()
    result = []
    for n in nodes:
        result.append({
            "id": n.id,
            "is_connected": n.is_connected,
            "is_virtual": n.token == VIRTUAL_NODE_TOKEN,
            "last_seen": n.last_seen,
        })
    return result


def get_node(db: Session, node_id: int):
    """获取单个节点详情。"""
    return NodeRepo(db).get(node_id)


def list_videos_by_node(db: Session, node_id: int):
    """列出某节点下的所有视频设备。"""
    return VideoDeviceRepo(db).by_node(node_id)


def list_audios_by_node(db: Session, node_id: int):
    """列出某节点下的所有音频设备。"""
    return AudioDeviceRepo(db).by_node(node_id)


def create_stream_device(
    db: Session,
    node_id: int,
    device_type: str,
    name: str,
    stream_url: str,
) -> dict | None:
    """向指定 Node 注册自定义流设备。

    不验证流可达性——对方负责将流推到 SRS 服务。

    Args:
        db: 数据库会话
        node_id: 目标 Node ID（通常是虚拟 Node）
        device_type: "video" 或 "audio"
        name: 设备名称
        stream_url: RTMP 流地址

    Returns:
        设备信息字典；Node 不存在时返回 None
    """
    # 1. 验证 Node 存在
    node = NodeRepo(db).get(node_id)
    if node is None:
        return None

    # 2. 创建 VideoDevice 或 AudioDevice
    if device_type == "video":
        repo = VideoDeviceRepo(db)
        device = repo.create(node_id=node_id, name=name, stream_url=stream_url)
    elif device_type == "audio":
        repo = AudioDeviceRepo(db)
        device = repo.create(node_id=node_id, name=name)
    else:
        return None

    db.commit()
    db.refresh(device)

    logger.info("Stream device created: type=%s name=%s node=%d url=%s",
                device_type, name, node_id, stream_url)

    return {
        "id": device.id,
        "name": device.name,
        "device_type": device_type,
        "node_id": node_id,
        "stream_url": stream_url if device_type == "video" else None,
    }


def delete_stream_device(
    db: Session,
    node_id: int,
    device_type: str,
    device_id: int,
) -> bool:
    """删除指定 Node 下的自定义流设备。

    Args:
        db: 数据库会话
        node_id: Node ID
        device_type: "video" 或 "audio"
        device_id: 设备 ID

    Returns:
        True 如果删除成功，False 如果设备不存在或类型无效
    """
    if device_type == "video":
        repo = VideoDeviceRepo(db)
    elif device_type == "audio":
        repo = AudioDeviceRepo(db)
    else:
        return False

    device = repo.get(device_id)
    if device is None or device.node_id != node_id:
        return False

    repo.delete(device_id)
    db.commit()
    return True


def list_stream_devices(db: Session, node_id: int) -> list[dict]:
    """列出指定 Node 下的所有设备（含 stream_url 信息）。

    Args:
        db: 数据库会话
        node_id: Node ID

    Returns:
        设备信息字典列表
    """
    devices: list[dict] = []
    for v in VideoDeviceRepo(db).by_node(node_id):
        devices.append({
            "id": v.id,
            "name": v.name,
            "device_type": "video",
            "node_id": v.node_id,
            "stream_url": v.stream_url,
            "streaming": v.streaming,
        })
    for a in AudioDeviceRepo(db).by_node(node_id):
        devices.append({
            "id": a.id,
            "name": a.name,
            "device_type": "audio",
            "node_id": a.node_id,
            "stream_url": None,
            "streaming": a.streaming,
        })
    return devices
