"""设备管理服务。"""

from sqlalchemy.orm import Session

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo


def list_nodes(db: Session) -> list:
    """获取所有 Node 列表。"""
    return NodeRepo(db).all()


def get_node_health(db: Session, node_id: int) -> dict | None:
    """获取指定 Node 的健康摘要。"""
    node_repo = NodeRepo(db)
    node = node_repo.get(node_id)
    if node is None:
        return None

    video_count = len(VideoDeviceRepo(db).by_node(node_id))
    audio_count = len(AudioDeviceRepo(db).by_node(node_id))

    # streaming 设备计数（Part A streaming 字段生效后用）
    streaming_count = 0
    try:
        videos = VideoDeviceRepo(db).by_node(node_id)
        audios = AudioDeviceRepo(db).by_node(node_id)
        streaming_count = sum(1 for v in videos if getattr(v, "streaming", False))
        streaming_count += sum(1 for a in audios if getattr(a, "streaming", False))
    except AttributeError:
        pass

    return {
        "node_id": node_id,
        "is_connected": getattr(node, "is_connected", False),
        "video_devices": video_count,
        "audio_devices": audio_count,
        "streaming_devices": streaming_count,
    }


def onboard_device(db: Session, node_id: int) -> bool:
    """触发设备接入流程。"""
    node = NodeRepo(db).get(node_id)
    if node is None:
        return False
    # 当前阶段：记录准备接入；后续由 WSS handler 触发实际设备发现
    return True
