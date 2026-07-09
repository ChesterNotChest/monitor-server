"""Node Task 门户 —— 节点与设备只读查询的轻量包装。

Router 不直接调 Repository，统一通过此模块访问，保持分层一致性。
"""

from sqlalchemy.orm import Session

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo


def list_nodes(db: Session):
    """列出所有计算机节点。"""
    return NodeRepo(db).all()


def get_node(db: Session, node_id: int):
    """获取单个节点详情。"""
    return NodeRepo(db).get(node_id)


def list_videos_by_node(db: Session, node_id: int):
    """列出某节点下的所有视频设备。"""
    return VideoDeviceRepo(db).by_node(node_id)


def list_audios_by_node(db: Session, node_id: int):
    """列出某节点下的所有音频设备。"""
    return AudioDeviceRepo(db).by_node(node_id)
