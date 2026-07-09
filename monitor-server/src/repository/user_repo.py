"""系统用户 Repository。"""

from sqlalchemy import select

from .base import BaseRepo
from ..models.user import User


class UserRepo(BaseRepo[User]):
    """系统用户数据访问层。"""

    model = User

    def by_username(self, username: str) -> User | None:
        """按用户名查询。"""
        return self.db.scalar(
            select(User).where(User.username == username)
        )
