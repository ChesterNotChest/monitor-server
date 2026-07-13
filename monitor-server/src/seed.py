"""数据库种子数据 —— 首次启动时创建默认管理员。

密码写入项目目录下的 ``admin_password.txt``，生产部署前删除此文件。
"""

import os
import secrets
import string

from src.extensions import SessionLocal
from src.repository.user_repo import UserRepo
from src.service.auth_task import hash_password

ADMIN_PASSWORD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "admin_password.txt"
)


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def seed_admin():
    """如果 users 表为空，创建管理员账户 + 演示安全员/负责人并写密码文件。"""
    db = SessionLocal()
    try:
        repo = UserRepo(db)
        if repo.count() > 0:
            return  # 已有用户，跳过种子

        password = _generate_password()
        admin = repo.create(
            username="admin",
            password_hash=hash_password(password),
            role="operator",
            is_active=True,
        )

        # 创建演示安全员和负责人，形成上报链
        guard = repo.create(
            username="security_guard_1",
            password_hash=hash_password("guard123"),
            role="security_guard",
            dingtalk_mobile="13800000001",
            supervisor_id=None,  # 暂不设上级，使用 role 上报
            is_active=True,
        )
        manager = repo.create(
            username="manager_1",
            password_hash=hash_password("manager123"),
            role="manager",
            dingtalk_mobile="13800000002",
            supervisor_id=None,
            is_active=True,
        )
        # 安全员 → 负责人 上报链
        guard.supervisor_id = manager.id

        db.commit()

        # 写密码文件
        with open(ADMIN_PASSWORD_FILE, "w", encoding="utf-8") as f:
            f.write(f"管理员账户\n用户名: admin\n密码: {password}\n")
            f.write("请在首次登录后修改密码，并在生产部署前删除此文件。\n")

        print(f"[seed] 已创建管理员账户 admin + 演示安全员/负责人，密码已写入 {ADMIN_PASSWORD_FILE}")
    finally:
        db.close()
