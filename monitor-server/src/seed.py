"""数据库种子数据 —— 首次启动时创建默认管理员。

密码写入项目目录下的 ``admin_password.txt``，生产部署前删除此文件。
"""

import os
import secrets
import string

from src.extensions import SessionLocal
from src.repository.user_repo import UserRepo
from src.service.auth_service import hash_password

ADMIN_PASSWORD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "admin_password.txt"
)


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def seed_admin():
    """如果 users 表为空，创建管理员账户并写密码文件。"""
    db = SessionLocal()
    try:
        repo = UserRepo(db)
        if repo.count() > 0:
            return  # 已有用户，跳过种子

        password = _generate_password()
        repo.create(
            username="admin",
            password_hash=hash_password(password),
            role="operator",
            is_active=True,
        )
        db.commit()

        # 写密码文件
        with open(ADMIN_PASSWORD_FILE, "w", encoding="utf-8") as f:
            f.write(f"管理员账户\n用户名: admin\n密码: {password}\n")
            f.write("请在首次登录后修改密码，并在生产部署前删除此文件。\n")

        print(f"[seed] 已创建管理员账户 admin，密码已写入 {ADMIN_PASSWORD_FILE}")
    finally:
        db.close()
