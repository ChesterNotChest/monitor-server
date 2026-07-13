"""种子数据脚本 —— 预置 AI 检测枚举值与异常规则。

用法: cd monitor-server && python -m src.seed_data
幂等：重复执行不报错、不重复插入。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.extensions import SessionLocal, Base, engine
from src.repository.entity_type_repo import EntityTypeRepo
from src.repository.action_type_repo import ActionTypeRepo
from src.repository.sound_type_repo import SoundTypeRepo
from src.repository.response_action_repo import ResponseActionRepo
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.face_recognition_result_repo import FaceRecognitionResultRepo
from src.constants import SeverityLevel
from src.models.alert_group import AlertGroup
from src.models.exception import ExceptionDef
from src.models.response_action import ResponseAction


def _upsert_enum(db: Session, repo_cls, name: str):
    """幂等插入枚举记录：按名称查找，存在则返回，不存在则创建。"""
    repo = repo_cls(db)
    existing = db.scalar(select(repo.model).where(repo.model.name == name))
    if existing:
        return existing
    return repo.create(name=name)


# ── 人脸识别结果 ────────────────────────────────

FACE_RESULTS = [
    ("NO_RESULT", "无结果"),
    ("STRANGER", "陌生人"),
    ("NORMAL", "正常"),
]

FACE_RESULT_MAP = {}  # name -> id, 供后续异常规则引用


def seed_face_recognition_results(db: Session) -> None:
    for name, display in FACE_RESULTS:
        obj = _upsert_enum(db, FaceRecognitionResultRepo, name)
        FACE_RESULT_MAP[name] = obj.id
    db.flush()
    print(f"  face_recognition_results: {len(FACE_RESULTS)} 条已就绪")


# ── YOLO 实体类型 ───────────────────────────────

ENTITY_NAMES = [
    "PERSON", "CAR", "TRUCK", "BUS", "MOTORCYCLE",
    "BICYCLE", "DOG", "CAT", "BIRD", "BACKPACK",
    "SUITCASE", "KNIFE", "GUN", "FIRE", "SMOKE",
]


def seed_entity_types(db: Session) -> None:
    for name in ENTITY_NAMES:
        _upsert_enum(db, EntityTypeRepo, name)
    db.flush()
    print(f"  entity_types: {len(ENTITY_NAMES)} 条已就绪")


# ── SlowFast 行为类型 ────────────────────────────

ACTION_NAMES = [
    "WALKING", "RUNNING", "FALLING", "FIGHTING", "LOITERING",
    "CROWDING", "CLIMBING", "THROWING", "POINTING", "WAVING",
    "HUGGING", "PUSHING", "LYING_DOWN", "SITTING", "STANDING",
    "SMOKING",
]


def seed_action_types(db: Session) -> None:
    for name in ACTION_NAMES:
        _upsert_enum(db, ActionTypeRepo, name)
    db.flush()
    print(f"  action_types: {len(ACTION_NAMES)} 条已就绪")


# ── YAMNet 声音类型 ─────────────────────────────

SOUND_NAMES = [
    "GUNSHOT", "SCREAM", "SIREN", "EXPLOSION", "GLASS_BREAKING",
    "DOG_BARKING", "CAR_HORN", "ENGINE", "BABY_CRYING", "ALARM",
    "THUNDER", "WIND", "RAIN", "FOOTSTEPS", "SILENCE",
]


def seed_sound_types(db: Session) -> None:
    for name in SOUND_NAMES:
        _upsert_enum(db, SoundTypeRepo, name)
    db.flush()
    print(f"  sound_types: {len(SOUND_NAMES)} 条已就绪")


# ── 响应动作 ────────────────────────────────────

RESPONSE_ACTIONS = [
    ("TRIGGER_RECORDING", None, None),
    ("SEND_NOTIFICATION", "dingtalk_webhook", None),  # config_json 从 .env DINGTALK_WEBHOOK_URL 读取
    ("ACTIVATE_ALARM", None, None),
    ("CALL_API", None, None),
    ("SEND_EMAIL", None, None),
]


def seed_response_actions(db: Session) -> dict[str, ResponseAction]:
    result = {}
    for name, channel, config_json in RESPONSE_ACTIONS:
        existing = db.scalar(select(ResponseAction).where(ResponseAction.name == name))
        if existing:
            if channel and not existing.channel:
                existing.channel = channel
            result[name] = existing
        else:
            result[name] = ResponseActionRepo(db).create(
                name=name, channel=channel, config_json=config_json
            )
    db.flush()
    print(f"  response_actions: {len(RESPONSE_ACTIONS)} 条已就绪")
    return result


# ── 告警分组 + 绑定响应动作 ─────────────────────

ALERT_GROUP_BINDINGS = [
    ("信息", []),
    ("警告", ["SEND_NOTIFICATION"]),
    ("严重", ["SEND_NOTIFICATION", "TRIGGER_RECORDING"]),
    ("紧急", ["ACTIVATE_ALARM", "SEND_NOTIFICATION", "CALL_API", "TRIGGER_RECORDING"]),
]


def seed_alert_groups(db: Session, responses: dict[str, ResponseAction]) -> None:
    for group_name, resp_names in ALERT_GROUP_BINDINGS:
        existing = db.scalar(select(AlertGroup).where(AlertGroup.name == group_name))
        if existing:
            group = existing
        else:
            group = AlertGroupRepo(db).create(name=group_name)

        for resp_name in resp_names:
            resp = responses[resp_name]
            if resp not in group.responses:
                group.responses.append(resp)
    db.flush()
    print(f"  alert_groups: {len(ALERT_GROUP_BINDINGS)} 条已就绪")


# ── 异常规则 + M2M 绑定 ─────────────────────────

EXCEPTION_RULES = [
    {
        "name": "入侵检测",
        "severity": SeverityLevel.CRITICAL,
        "group": "严重",
        "entities": ["PERSON"],
        "actions": [],
        "sounds": [],
        "face_result": "STRANGER",
    },
    {
        "name": "暴力事件",
        "severity": SeverityLevel.EMERGENCY,
        "group": "紧急",
        "entities": ["PERSON"],
        "actions": ["FIGHTING", "PUSHING", "FALLING"],
        "sounds": [],
        "face_result": None,
    },
    {
        "name": "武器检测",
        "severity": SeverityLevel.EMERGENCY,
        "group": "紧急",
        "entities": ["KNIFE", "GUN"],
        "actions": [],
        "sounds": [],
        "face_result": None,
    },
    {
        "name": "火灾检测",
        "severity": SeverityLevel.EMERGENCY,
        "group": "紧急",
        "entities": ["FIRE", "SMOKE"],
        "actions": [],
        "sounds": [],
        "face_result": None,
    },
    {
        "name": "声音异常",
        "severity": SeverityLevel.EMERGENCY,
        "group": "紧急",
        "entities": [],
        "actions": [],
        "sounds": ["GUNSHOT", "SCREAM", "EXPLOSION"],
        "face_result": None,
    },
    {
        "name": "非法攀爬",
        "severity": SeverityLevel.WARNING,
        "group": "警告",
        "entities": ["PERSON"],
        "actions": ["CLIMBING"],
        "sounds": [],
        "face_result": None,
    },
    {
        "name": "人员倒地",
        "severity": SeverityLevel.CRITICAL,
        "group": "严重",
        "entities": ["PERSON"],
        "actions": ["LYING_DOWN"],
        "sounds": [],
        "face_result": None,
    },
    {
        "name": "可疑徘徊",
        "severity": SeverityLevel.WARNING,
        "group": "警告",
        "entities": ["PERSON"],
        "actions": ["LOITERING"],
        "sounds": [],
        "face_result": None,
    },
]


def seed_exceptions(db: Session) -> None:
    from src.models.entity_type import EntityType
    from src.models.action_type import ActionType
    from src.models.sound_type import SoundType

    # 预加载所有枚举的 name→obj 映射
    entity_map = {e.name: e for e in db.scalars(select(EntityType)).all()}
    action_map = {a.name: a for a in db.scalars(select(ActionType)).all()}
    sound_map = {s.name: s for s in db.scalars(select(SoundType)).all()}
    group_map = {g.name: g for g in db.scalars(
        select(AlertGroup).where(AlertGroup.name.in_(["信息", "警告", "严重", "紧急"]))
    ).all()}

    for rule in EXCEPTION_RULES:
        # 幂等：按 name 查重
        existing = db.scalar(select(ExceptionDef).where(ExceptionDef.name == rule["name"]))
        if existing:
            exc = existing
        else:
            face_result_id = FACE_RESULT_MAP.get(rule["face_result"]) if rule["face_result"] else None
            exc = ExceptionDefRepo(db).create(
                name=rule["name"],
                severity=rule["severity"],
                group_id=group_map[rule["group"]].id,
                face_result_id=face_result_id,
            )

        # M2M 绑定
        for ename in rule["entities"]:
            entity = entity_map.get(ename)
            if entity and entity not in exc.entities:
                exc.entities.append(entity)
        for aname in rule["actions"]:
            action = action_map.get(aname)
            if action and action not in exc.actions:
                exc.actions.append(action)
        for sname in rule["sounds"]:
            sound = sound_map.get(sname)
            if sound and sound not in exc.sounds:
                exc.sounds.append(sound)

    db.flush()
    print(f"  exceptions: {len(EXCEPTION_RULES)} 条已就绪")


# ── 入口 ────────────────────────────────────────


def main():
    """执行所有种子数据插入。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("=== 种子数据脚本 ===")
        seed_face_recognition_results(db)
        seed_entity_types(db)
        seed_action_types(db)
        seed_sound_types(db)
        responses = seed_response_actions(db)
        seed_alert_groups(db, responses)
        seed_exceptions(db)
        db.commit()
        print("=== 种子数据完成 ===")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
