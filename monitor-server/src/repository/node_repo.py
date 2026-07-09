"""Node 数据访问。"""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.models import AudioDevice, Node, VideoDevice


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def get_all(db: Session) -> list[Node]:
    return list(db.scalars(select(Node)).all())


def get_by_id(db: Session, node_id: int) -> Node | None:
    return db.get(Node, node_id)


def get_by_token(db: Session, token: str) -> Node | None:
    token_hash = hash_token(token)
    return db.scalar(select(Node).where(Node.token == token_hash))


def update_connection_status(db: Session, node_id: int, is_connected: bool) -> Node | None:
    node = get_by_id(db, node_id)
    if node is None:
        return None

    node.is_connected = is_connected
    node.last_seen = datetime.now(timezone.utc)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def reset_device_streaming_by_node(db: Session, node_id: int) -> None:
    db.execute(
        update(VideoDevice)
        .where(VideoDevice.node_id == node_id)
        .values(streaming=False)
    )
    db.execute(
        update(AudioDevice)
        .where(AudioDevice.node_id == node_id)
        .values(streaming=False)
    )
    db.commit()
