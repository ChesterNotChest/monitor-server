"""用户管理服务 —— 运维员专用。"""

from sqlalchemy.orm import Session

from src.repository.user_repo import UserRepo
from src.service.auth_task import hash_password


def list_users(db: Session) -> list:
    """列出所有用户。"""
    return UserRepo(db).all()


def create_user(db: Session, username: str, password: str, role: str,
                dingtalk_mobile: str | None = None,
                supervisor_id: int | None = None) -> dict:
    """创建新用户。"""
    repo = UserRepo(db)
    existing = repo.by_username(username)
    if existing is not None:
        raise ValueError(f"用户名 {username} 已存在")
    return repo.create(
        username=username,
        password_hash=hash_password(password),
        role=role,
        dingtalk_mobile=dingtalk_mobile,
        supervisor_id=supervisor_id,
    )


def update_user(db: Session, user_id: int, **kwargs):
    """更新用户信息。"""
    return UserRepo(db).update(user_id, **kwargs)


def update_role(db: Session, user_id: int, role: str):
    """修改用户角色。"""
    return UserRepo(db).update(user_id, role=role)


def deactivate_user(db: Session, user_id: int) -> bool:
    """停用用户（软删除）。"""
    user = UserRepo(db).update(user_id, is_active=False)
    return user is not None
