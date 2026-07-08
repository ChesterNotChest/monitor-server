"""计算机节点 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.node import Node


class NodeRepo(BaseRepo[Node]):
    """计算机节点数据访问层。"""

    model = Node

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def by_token(self, token: str) -> Node | None:
        """按认证令牌查找节点。"""
        return self.db.query(Node).filter(Node.token == token).first()
