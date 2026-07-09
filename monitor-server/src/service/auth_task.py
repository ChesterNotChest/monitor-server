"""认证服务 —— JWT 签发/验证、密码哈希。"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config import settings
from src.repository.user_repo import UserRepo


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码匹配 bcrypt 哈希。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, username: str, role: str) -> str:
    """签发 JWT access token。"""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """验证 JWT，返回 payload 或 None。"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def login(db: Session, username: str, password: str) -> dict | None:
    """验证用户名密码，返回 {access_token, user} 或 None。"""
    repo = UserRepo(db)
    user = repo.by_username(username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    token = create_token(user.id, user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


def get_me(db: Session, user_id: int):
    """按 ID 返回当前用户。"""
    return UserRepo(db).get(user_id)
