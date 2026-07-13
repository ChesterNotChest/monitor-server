"""数据库种子数据 —— 首次启动时创建默认管理员和告警规则。

密码写入项目目录下的 ``admin_password.txt``，生产部署前删除此文件。
"""

import json
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

# 全量对齐 constants.py 枚举值。AI 管线输出固定整数 ID，生产库最终也应
# 与这些 ID/name 对齐；seed_alerts 负责幂等补缺，历史错位库需先迁移。
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
    "spoof",        # FaceRecognitionResult.SPOOF = 4
]

_DEFAULT_GROUP_NAME = "默认告警组"
_DEFAULT_EXCEPTION_NAME = "人员出现"
_DEFAULT_RESPONSE_ACTIONS = [
    ("TRIGGER_RECORDING", None),
    ("SEND_NOTIFICATION", "dingtalk_webhook"),
    ("ACTIVATE_ALARM", None),
    ("CALL_API", None),
    ("SEND_EMAIL", None),
]


def seed_virtual_node():
    """如果 nodes 表无虚拟 Node，创建常驻虚拟 Node（is_connected=False）。

    虚拟 Node 不接受 WSS 连接，专门承载外部 RTMP 流设备。
    通过预留 token 识别，重复调用不重复插入（idempotent）。
    """
    from src.constants import VIRTUAL_NODE_TOKEN
    from src.models.node import Node

    db = SessionLocal()
    try:
        existing = db.query(Node).filter(Node.token == VIRTUAL_NODE_TOKEN).first()
        if existing is not None:
            return
        node = Node(token=VIRTUAL_NODE_TOKEN, is_connected=False)
        db.add(node)
        db.commit()
        print("[seed] 已创建虚拟 Node (is_connected=False)")
    finally:
        db.close()


def seed_alerts():
    """幂等补齐告警相关基础种子数据。

    存量数据库可能只有一部分旧枚举。这里按名称补缺，不清表；
    若历史库已经出现 ID/name 错位，需要先做一次枚举迁移。
    """
    from src.models.entity_type import EntityType
    from src.models.action_type import ActionType
    from src.models.sound_type import SoundType
    from src.models.face_recognition_result import FaceRecognitionResult
    from src.models.alert_group import AlertGroup
    from src.models.exception import ExceptionDef, exception_entities
    from src.models.response_action import ResponseAction, alert_group_responses
    from src.config import settings

    db = SessionLocal()
    try:
        def get_or_create_by_name(model, name):
            obj = db.query(model).filter(model.name == name).first()
            if obj is None:
                obj = model(name=name)
                db.add(obj)
                db.flush()
            return obj

        for name in _ENTITY_NAMES:
            get_or_create_by_name(EntityType, name)

        for name in _ACTION_NAMES:
            get_or_create_by_name(ActionType, name)

        for name in _SOUND_NAMES:
            get_or_create_by_name(SoundType, name)

        for name in _FACE_RESULT_NAMES:
            get_or_create_by_name(FaceRecognitionResult, name)

        # FenceEventType 由 seed_fence_events() 负责按 id=1/2 精确补齐，避免
        # 存量库已有 ENTERED/TOO_CLOSE 时再插入 lowercase 重复语义数据。

        group = get_or_create_by_name(AlertGroup, _DEFAULT_GROUP_NAME)

        responses = {}
        webhook_url = settings.DINGTALK_WEBHOOK_URL or os.getenv("DINGTALK_WEBHOOK", "")
        for name, channel in _DEFAULT_RESPONSE_ACTIONS:
            response = get_or_create_by_name(ResponseAction, name)
            if channel and not response.channel:
                response.channel = channel
            if name == "SEND_NOTIFICATION" and webhook_url and not response.config_json:
                response.config_json = json.dumps({"webhook_url": webhook_url})
            responses[name] = response

        notification = responses.get("SEND_NOTIFICATION")
        if notification is not None:
            groups_to_bind = [group]
            has_any_response_binding = db.execute(
                alert_group_responses.select().limit(1)
            ).first() is not None
            if not has_any_response_binding:
                groups_to_bind = db.query(AlertGroup).all()

            for target_group in groups_to_bind:
                linked = db.execute(
                    alert_group_responses.select().where(
                        alert_group_responses.c.group_id == target_group.id,
                        alert_group_responses.c.response_id == notification.id,
                    )
                ).first()
                if linked is None:
                    db.execute(
                        alert_group_responses.insert().values(
                            group_id=target_group.id,
                            response_id=notification.id,
                        )
                    )

        exc = db.query(ExceptionDef).filter(
            ExceptionDef.name == _DEFAULT_EXCEPTION_NAME
        ).first()
        if exc is None:
            exc = ExceptionDef(
                name=_DEFAULT_EXCEPTION_NAME,
                severity=SeverityLevel.WARNING,
                group_id=group.id,
            )
            db.add(exc)
            db.flush()

        person = db.query(EntityType).filter(EntityType.name == "person").first()
        if person is not None:
            linked = db.execute(
                exception_entities.select().where(
                    exception_entities.c.exception_id == exc.id,
                    exception_entities.c.entity_id == person.id,
                )
            ).first()
            if linked is None:
                db.execute(
                    exception_entities.insert().values(
                        exception_id=exc.id,
                        entity_id=person.id,
                    )
                )

        db.commit()
        print(
            f"[seed] 告警种子已就绪: "
            f"entities={len(_ENTITY_NAMES)}, "
            f"actions={len(_ACTION_NAMES)}, "
            f"sounds={len(_SOUND_NAMES)}, "
            f"face_results={len(_FACE_RESULT_NAMES)}, "
            f"responses={len(_DEFAULT_RESPONSE_ACTIONS)}, "
            f"group='{_DEFAULT_GROUP_NAME}', "
            f"exception='{_DEFAULT_EXCEPTION_NAME}'"
        )
    finally:
        db.close()


def seed_fence_events():
    """精确幂等：确保 FenceEventType 表同时存在 id=1 (ENTERED) 和 id=2 (TOO_CLOSE)。

    与 seed_alerts() 独立；此函数处理存量 DB 只有 id=1 或缺少围栏枚举的场景。
    """
    from src.models.fence_event_type import FenceEventType

    db = SessionLocal()
    try:
        existing_ids = {r.id for r in db.query(FenceEventType).all()}
        if 1 in existing_ids and 2 in existing_ids:
            return
        if 1 not in existing_ids:
            db.add(FenceEventType(id=1, name="ENTERED"))
        if 2 not in existing_ids:
            db.add(FenceEventType(id=2, name="TOO_CLOSE"))
        db.commit()
        print("[seed] fence_event_types: id=1 ENTERED / id=2 TOO_CLOSE 已就绪")
    finally:
        db.close()
