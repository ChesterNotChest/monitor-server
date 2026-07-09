"""SituationEventRepo 冒烟测试。"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.situation_event_repo import SituationEventRepo
from src.constants import SeverityLevel


class TestSituationEventRepo:
    @pytest.fixture
    def view_and_exception(self, db):
        node = NodeRepo(db).create(token="event-test-node")
        video = VideoDeviceRepo(db).create(name="event-cam", node_id=node.id)
        audio = AudioDeviceRepo(db).create(name="event-mic", node_id=node.id)
        view = MonitorViewRepo(db).create(video_id=video.id, audio_id=audio.id)
        ag = AlertGroupRepo(db).create(name="事件测试分组")
        exc = ExceptionDefRepo(db).create(severity=SeverityLevel.WARNING, group_id=ag.id)
        return view, exc

    def test_create_and_get(self, db, view_and_exception):
        view, exc = view_and_exception
        repo = SituationEventRepo(db)
        se = repo.create(view_id=view.id, exception_id=exc.id)
        assert se.id is not None
        assert repo.get(se.id).view_id == view.id

    def test_by_view(self, db, view_and_exception):
        view, exc = view_and_exception
        repo = SituationEventRepo(db)
        repo.create(view_id=view.id, exception_id=exc.id)
        repo.create(view_id=view.id, exception_id=exc.id)
        events = repo.by_view(view.id)
        assert len(events) == 2
        # 按时间倒序验证
        assert events[0].timestamp >= events[1].timestamp

    def test_by_view_empty(self, db):
        repo = SituationEventRepo(db)
        assert len(repo.by_view(99999)) == 0

    def test_by_time_range(self, db, view_and_exception):
        view, exc = view_and_exception
        repo = SituationEventRepo(db)
        repo.create(view_id=view.id, exception_id=exc.id)
        now = datetime.now(timezone.utc)
        events = repo.by_time_range(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert len(events) >= 1

    def test_by_time_range_out_of_bounds(self, db, view_and_exception):
        view, exc = view_and_exception
        repo = SituationEventRepo(db)
        repo.create(view_id=view.id, exception_id=exc.id)
        past = datetime(2020, 1, 1)
        events = repo.by_time_range(start=past, end=past + timedelta(days=1))
        assert len(events) == 0

    def test_delete(self, db, view_and_exception):
        view, exc = view_and_exception
        repo = SituationEventRepo(db)
        se = repo.create(view_id=view.id, exception_id=exc.id)
        assert repo.delete(se.id) is True

    def test_fk_view_violation(self, db, view_and_exception):
        _, exc = view_and_exception
        repo = SituationEventRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(view_id=99999, exception_id=exc.id)

    def test_fk_exception_violation(self, db, view_and_exception):
        view, _ = view_and_exception
        repo = SituationEventRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(view_id=view.id, exception_id=99999)
