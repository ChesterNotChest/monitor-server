"""数据库种子数据 —— 首次启动时创建默认管理员和告警规则。

密码写入项目目录下的 ``admin_password.txt``，生产部署前删除此文件。
"""

import os
import secrets
import string

from src.extensions import SessionLocal
from src.repository.user_repo import UserRepo
from src.service.auth_task import hash_password
from src.constants import SeverityLevel

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
            return

        password = _generate_password()
        repo.create(
            username="admin",
            password_hash=hash_password(password),
            role="operator",
            is_active=True,
        )
        db.commit()

        with open(ADMIN_PASSWORD_FILE, "w", encoding="utf-8") as f:
            f.write(f"管理员账户\n用户名: admin\n密码: {password}\n")
            f.write("请在首次登录后修改密码，并在生产部署前删除此文件。\n")

        print(f"[seed] 已创建管理员账户 admin，密码已写入 {ADMIN_PASSWORD_FILE}")
    finally:
        db.close()


# ── 告警种子 ────────────────────────────────────

_ENTITY_NAMES = ["person", "car", "dog", "cat"]
_ACTION_NAMES = ["running", "fighting", "falling"]
_SOUND_NAMES = ["glass_break", "scream", "gunshot"]
_DEFAULT_GROUP_NAME = "默认告警组"
_DEFAULT_EXCEPTION_NAME = "人员出现"


def seed_alerts():
    """如果告警相关表为空，预置基础种子数据。"""
    from src.models.entity_type import EntityType
    from src.models.action_type import ActionType
    from src.models.sound_type import SoundType
    from src.models.alert_group import AlertGroup
    from src.models.exception import ExceptionDef, exception_entities

    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(EntityType).first()
        if existing is not None:
            return

        # EntityType
        entities = {}
        for name in _ENTITY_NAMES:
            e = EntityType(name=name)
            db.add(e)
            entities[name] = e
        db.flush()

        # ActionType
        for name in _ACTION_NAMES:
            db.add(ActionType(name=name))
        db.flush()

        # SoundType
        for name in _SOUND_NAMES:
            db.add(SoundType(name=name))
        db.flush()

        # AlertGroup
        group = AlertGroup(name=_DEFAULT_GROUP_NAME)
        db.add(group)
        db.flush()

        # ExceptionDef: 人员出现
        exc = ExceptionDef(
            name=_DEFAULT_EXCEPTION_NAME,
            severity=SeverityLevel.WARNING,
            group_id=group.id,
        )
        db.add(exc)
        db.flush()

        # 关联 person 实体类型
        db.execute(
            exception_entities.insert().values(
                exception_id=exc.id, entity_id=entities["person"].id
            )
        )

        db.commit()
        print(
            f"[seed] 已创建告警种子: "
            f"entities={len(_ENTITY_NAMES)}, "
            f"actions={len(_ACTION_NAMES)}, "
            f"sounds={len(_SOUND_NAMES)}, "
            f"group='{_DEFAULT_GROUP_NAME}', "
            f"exception='{_DEFAULT_EXCEPTION_NAME}'"
        )
    finally:
        db.close()
