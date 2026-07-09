"""event_task 服务层冒烟测试。"""

from datetime import datetime, timedelta

from src.service.event_task import list_events, get_event, stats_by_exception, stats_trend
from src.repository.situation_event_repo import SituationEventRepo


class TestEventQuery:
    def test_list_empty(self, db):
        items, total = list_events(db)
        assert total == 0

    def test_get_nonexistent(self, db):
        assert get_event(db, 99999) is None

    def test_list_with_filters(self, db):
        # Create required FK references first
        from src.repository.node_repo import NodeRepo
        from src.repository.video_device_repo import VideoDeviceRepo
        from src.repository.audio_device_repo import AudioDeviceRepo
        from src.repository.monitor_view_repo import MonitorViewRepo
        from src.repository.alert_group_repo import AlertGroupRepo
        from src.repository.exception_def_repo import ExceptionDefRepo
        from src.constants import SeverityLevel

        node = NodeRepo(db).create(token="test-token")
        vdev = VideoDeviceRepo(db).create(name="v1", node_id=node.id)
        adev = AudioDeviceRepo(db).create(name="a1", node_id=node.id)
        view = MonitorViewRepo(db).create(video_id=vdev.id, audio_id=adev.id)
        group = AlertGroupRepo(db).create(name="test-group")
        exc = ExceptionDefRepo(db).create(severity=SeverityLevel.CRITICAL, group_id=group.id)

        # Insert via repo
        repo = SituationEventRepo(db)
        now = datetime.utcnow()
        repo.create(view_id=view.id, exception_id=exc.id, timestamp=now)

        items, total = list_events(db, view_id=view.id)
        assert total >= 1

        # Time range
        items2, _ = list_events(
            db, start=now - timedelta(hours=1), end=now + timedelta(hours=1)
        )
        assert len(items2) >= 1


class TestStats:
    def test_stats_by_exception_empty(self, db):
        rows = stats_by_exception(db)
        assert isinstance(rows, list)

    def test_stats_trend_empty(self, db):
        rows = stats_trend(db)
        assert isinstance(rows, list)

    def test_stats_trend_with_granularity(self, db):
        for g in ("hour", "day", "month"):
            rows = stats_trend(db, granularity=g)
            assert isinstance(rows, list)
