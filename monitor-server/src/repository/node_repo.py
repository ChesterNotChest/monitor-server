"""计算机节点 Repository。"""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.audio_device import AudioDevice
from ..models.node import Node
from ..models.video_device import VideoDevice


def hash_token(token: str) -> str:
    """对 Node token 做 SHA256 摘要。"""

    return sha256(token.encode("utf-8")).hexdigest()


class NodeRepo(BaseRepo[Node]):
    """计算机节点数据访问层。"""

    model = Node

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def by_token(self, token: str) -> Node | None:
        """按认证令牌查找节点。

        优先按 SHA256 摘要匹配；为兼容历史数据和现有测试，未命中时回退到明文匹配。
        """

        token_hash = hash_token(token)
        node = self.db.query(Node).filter(Node.token == token_hash).first()
        if node is not None:
            return node
        return self.db.query(Node).filter(Node.token == token).first()

    def update_connection_status(
        self,
        node_id: int,
        is_connected: bool,
        last_seen: datetime | None = None,
    ) -> Node | None:
        """更新 Node 连接状态与最后活跃时间。"""

        node = self.get(node_id)
        if node is None:
            return None

        node.is_connected = is_connected
        node.last_seen = last_seen or datetime.now(timezone.utc)
        self.db.add(node)
        self.db.flush()
        return node

    def reset_device_streaming_by_node(self, node_id: int) -> None:
        """断连时清理该 Node 下所有音视频设备的推流状态。"""

        self.db.query(VideoDevice).filter(VideoDevice.node_id == node_id).update(
            {"streaming": False},
            synchronize_session=False,
        )
        self.db.query(AudioDevice).filter(AudioDevice.node_id == node_id).update(
            {"streaming": False},
            synchronize_session=False,
        )
        self.db.flush()


def get_all(db: Session) -> list[Node]:
    return NodeRepo(db).all()


def get_by_id(db: Session, node_id: int) -> Node | None:
    return NodeRepo(db).get(node_id)


def get_by_token(db: Session, token: str) -> Node | None:
    return NodeRepo(db).by_token(token)


def update_connection_status(db: Session, node_id: int, is_connected: bool) -> Node | None:
    node = NodeRepo(db).update_connection_status(node_id, is_connected)
    db.commit()
    if node is not None:
        db.refresh(node)
    return node


def reset_device_streaming_by_node(db: Session, node_id: int) -> None:
    NodeRepo(db).reset_device_streaming_by_node(node_id)
    db.commit()
