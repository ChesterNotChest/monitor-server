"""用户服务层。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.repository.user_repo import UserRepo
from src.models.user import User


class UserNameConflictError(Exception):
    pass


def create_user(db: Session, username: str, role: int) -> User:
    try:
        return UserRepo(db).create(username=username, role=role)
    except IntegrityError:
        db.rollback()
        raise UserNameConflictError(f"用户名 '{username}' 已存在")


def list_users(db: Session) -> list[User]:
    return UserRepo(db).all(limit=1000)
