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
    """如果 users 表为空，创建管理员账户。密码从 ADMIN_DEFAULT_PASSWORD 配置读取。"""
    from src.config import settings
    db = SessionLocal()
    try:
        repo = UserRepo(db)
        if repo.count() > 0:
            return

        password = settings.ADMIN_DEFAULT_PASSWORD
        repo.create(
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

        print(f"[seed] 已创建管理员账户 admin，密码={password}")
    finally:
        db.close()


# ── 告警种子 ────────────────────────────────────

# 全量对齐 constants.py 枚举值，按 IntEnum 顺序插入使 auto-increment ID = 枚举值
_ENTITY_NAMES = [
    "person",       # YOLOEntityType.PERSON = 1
    "car",          # YOLOEntityType.CAR = 2
    "truck",        # YOLOEntityType.TRUCK = 3
    "bus",          # YOLOEntityType.BUS = 4
    "motorcycle",   # YOLOEntityType.MOTORCYCLE = 5
    "bicycle",      # YOLOEntityType.BICYCLE = 6
    "dog",          # YOLOEntityType.DOG = 7
    "cat",          # YOLOEntityType.CAT = 8
    "bird",         # YOLOEntityType.BIRD = 9
    "backpack",     # YOLOEntityType.BACKPACK = 10
    "suitcase",     # YOLOEntityType.SUITCASE = 11
    "knife",        # YOLOEntityType.KNIFE = 12
]

_ACTION_NAMES = [
    "walking",      # SlowFastActionType.WALKING = 1
    "running",      # SlowFastActionType.RUNNING = 2
    "falling",      # SlowFastActionType.FALLING = 3
    "fighting",     # SlowFastActionType.FIGHTING = 4
    "climbing",     # SlowFastActionType.CLIMBING = 5
    "throwing",     # SlowFastActionType.THROWING = 6
    "pointing",     # SlowFastActionType.POINTING = 7
    "waving",       # SlowFastActionType.WAVING = 8
    "hugging",      # SlowFastActionType.HUGGING = 9
    "pushing",      # SlowFastActionType.PUSHING = 10
    "sitting",      # SlowFastActionType.SITTING = 11
    "standing",     # SlowFastActionType.STANDING = 12
    "smoking",      # SlowFastActionType.SMOKING = 13
    "lying_down",   # SlowFastActionType.LYING_DOWN = 14
    "loitering",    # SlowFastActionType.LOITERING = 15
    "crowding",     # SlowFastActionType.CROWDING = 16
]

_SOUND_NAMES = [
    "gunshot",          # YAMNetSoundType.GUNSHOT = 1
    "scream",           # YAMNetSoundType.SCREAM = 2
    "siren",            # YAMNetSoundType.SIREN = 3
    "explosion",        # YAMNetSoundType.EXPLOSION = 4
    "glass_breaking",   # YAMNetSoundType.GLASS_BREAKING = 5
    "dog_barking",      # YAMNetSoundType.DOG_BARKING = 6
    "car_horn",         # YAMNetSoundType.CAR_HORN = 7
    "engine",           # YAMNetSoundType.ENGINE = 8
    "baby_crying",      # YAMNetSoundType.BABY_CRYING = 9
    "alarm",            # YAMNetSoundType.ALARM = 10
    "thunder",          # YAMNetSoundType.THUNDER = 11
    "wind",             # YAMNetSoundType.WIND = 12
    "rain",             # YAMNetSoundType.RAIN = 13
    "footsteps",        # YAMNetSoundType.FOOTSTEPS = 14
    "silence",          # YAMNetSoundType.SILENCE = 15
]

_FACE_RESULT_NAMES = [
    "no_result",    # FaceRecognitionResult.NO_RESULT = 1
    "stranger",     # FaceRecognitionResult.STRANGER = 2
    "normal",       # FaceRecognitionResult.NORMAL = 3
]

_FENCE_EVENT_NAMES = [
    "entered",      # FenceEventResult.ENTERED = 1
]

_DEFAULT_GROUP_NAME = "默认告警组"
_DEFAULT_EXCEPTION_NAME = "人员出现"


def seed_alerts():
    """如果告警相关表为空，预置基础种子数据。

    按 IntEnum 顺序插入使 DB auto-increment ID == 枚举整数值。
    重复调用不重复插入（idempotent）。
    """
    from src.models.entity_type import EntityType
    from src.models.action_type import ActionType
    from src.models.sound_type import SoundType
    from src.models.face_recognition_result import FaceRecognitionResult
    from src.models.fence_event_type import FenceEventType
    from src.models.alert_group import AlertGroup
    from src.models.exception import ExceptionDef, exception_entities

    db = SessionLocal()
    try:
        # idempotent: 已有数据则跳过
        existing = db.query(EntityType).first()
        if existing is not None:
            return

        # EntityType (12)
        for name in _ENTITY_NAMES:
            db.add(EntityType(name=name))
        db.flush()

        # ActionType (16)
        for name in _ACTION_NAMES:
            db.add(ActionType(name=name))
        db.flush()

        # SoundType (15)
        for name in _SOUND_NAMES:
            db.add(SoundType(name=name))
        db.flush()

        # FaceRecognitionResult (3)
        for name in _FACE_RESULT_NAMES:
            db.add(FaceRecognitionResult(name=name))
        db.flush()

        # FenceEventType (1)
        for name in _FENCE_EVENT_NAMES:
            db.add(FenceEventType(name=name))
        db.flush()

        # AlertGroup
        group = AlertGroup(name=_DEFAULT_GROUP_NAME)
        db.add(group)
        db.flush()

        # ExceptionDef: 人员出现（关联 person 实体类型）
        person_id = 1  # YOLOEntityType.PERSON = 1 = EntityType.id
        exc = ExceptionDef(
            name=_DEFAULT_EXCEPTION_NAME,
            severity=SeverityLevel.WARNING,
            group_id=group.id,
        )
        db.add(exc)
        db.flush()

        db.execute(
            exception_entities.insert().values(
                exception_id=exc.id, entity_id=person_id,
            )
        )

        db.commit()
        print(
            f"[seed] 已创建告警种子: "
            f"entities={len(_ENTITY_NAMES)}, "
            f"actions={len(_ACTION_NAMES)}, "
            f"sounds={len(_SOUND_NAMES)}, "
            f"face_results={len(_FACE_RESULT_NAMES)}, "
            f"fence_events={len(_FENCE_EVENT_NAMES)}, "
            f"group='{_DEFAULT_GROUP_NAME}', "
            f"exception='{_DEFAULT_EXCEPTION_NAME}'"
        )
    finally:
        db.close()
