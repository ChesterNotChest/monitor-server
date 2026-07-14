"""Seed data backfill tests."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.extensions import Base
import src.models  # noqa: F401 - register SQLAlchemy models
from src.models.action_type import ActionType
from src.models.alert_group import AlertGroup
from src.models.entity_type import EntityType
from src.models.exception import ExceptionDef
from src.models.face_recognition_result import FaceRecognitionResult
from src.models.response_action import ResponseAction, alert_group_responses
from src.models.sound_type import SoundType
from src.seed import seed_alerts


class _SessionLocal:
    def __init__(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    def __call__(self):
        return self.session_factory()

    def dispose(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()


def _names(db, model):
    return {row.name for row in db.query(model).all()}


def test_seed_alerts_backfills_partial_enum_tables(monkeypatch):
    session_local = _SessionLocal()
    monkeypatch.setattr("src.seed.SessionLocal", session_local)
    try:
        db = session_local()
        db.add_all(
            [
                EntityType(name="person"),
                EntityType(name="car"),
                EntityType(name="dog"),
                EntityType(name="cat"),
                ActionType(name="running"),
                ActionType(name="fighting"),
                ActionType(name="falling"),
                SoundType(name="gunshot"),
                SoundType(name="scream"),
                SoundType(name="glass_breaking"),
            ]
        )
        db.commit()
        db.close()

        seed_alerts()
        seed_alerts()

        db = session_local()
        assert db.query(EntityType).count() == 12
        assert db.query(ActionType).count() == 16
        assert db.query(SoundType).count() == 23  # 15 originals + 8 new
        assert db.query(FaceRecognitionResult).count() == 4  # NO_RESULT, STRANGER, NORMAL, SPOOF
        assert db.query(AlertGroup).filter_by(name="默认告警组").count() == 1
        assert db.query(ExceptionDef).filter_by(name="陌生人").count() == 1
        assert db.query(ResponseAction).count() == 5

        group = db.query(AlertGroup).filter_by(name="默认告警组").one()
        notification = db.query(ResponseAction).filter_by(name="SEND_NOTIFICATION").one()
        assert notification.channel == "dingtalk_webhook"
        linked = db.execute(
            alert_group_responses.select().where(
                alert_group_responses.c.group_id == group.id,
                alert_group_responses.c.response_id == notification.id,
            )
        ).first()
        assert linked is not None
        assert {"no_result", "stranger", "normal"} <= _names(
            db, FaceRecognitionResult
        )
        assert {"truck", "bus", "motorcycle", "bicycle", "knife"} <= _names(
            db, EntityType
        )
        db.close()
    finally:
        session_local.dispose()


def test_seed_alerts_binds_notification_to_existing_unbound_groups(monkeypatch):
    session_local = _SessionLocal()
    monkeypatch.setattr("src.seed.SessionLocal", session_local)
    try:
        db = session_local()
        legacy_group = AlertGroup(name="legacy-alert-group")
        db.add(legacy_group)
        db.commit()
        legacy_group_id = legacy_group.id
        db.close()

        seed_alerts()

        db = session_local()
        notification = db.query(ResponseAction).filter_by(name="SEND_NOTIFICATION").one()
        linked = db.execute(
            alert_group_responses.select().where(
                alert_group_responses.c.group_id == legacy_group_id,
                alert_group_responses.c.response_id == notification.id,
            )
        ).first()
        assert linked is not None
        db.close()
    finally:
        session_local.dispose()
