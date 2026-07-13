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
        assert db.query(SoundType).count() == 15
        assert db.query(FaceRecognitionResult).count() == 3
        assert db.query(AlertGroup).filter_by(name="默认告警组").count() == 1
        assert db.query(ExceptionDef).filter_by(name="人员出现").count() == 1
        assert {"no_result", "stranger", "normal"} <= _names(
            db, FaceRecognitionResult
        )
        assert {"truck", "bus", "motorcycle", "bicycle", "knife"} <= _names(
            db, EntityType
        )
        db.close()
    finally:
        session_local.dispose()
