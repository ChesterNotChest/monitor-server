"""告警处理服务测试。"""

import pytest

from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.alert_review_repo import AlertReviewRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.node_repo import NodeRepo
from src.repository.situation_event_repo import SituationEventRepo
from src.repository.user_repo import UserRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.service.alert_service import list_alerts, mark_handled, mark_false_alarm
from src.service.auth_service import hash_password
from src.constants import Role, SeverityLevel


@pytest.fixture
def setup_alert_scenario(db):
    """创建完整告警场景：User + Node + Devices + AlertGroup + ExceptionDef + View + SituationEvent。"""
    user = UserRepo(db).create(
        username="alert_test_user",
        password_hash=hash_password("pw"),
        role=Role.SECURITY_GUARD,
    )
    node = NodeRepo(db).create(token="alert-node")
    vd = VideoDeviceRepo(db).create(name="alert-cam", node_id=node.id)
    ad = AudioDeviceRepo(db).create(name="alert-mic", node_id=node.id)
    view = MonitorViewRepo(db).create(video_id=vd.id, audio_id=ad.id)
    group = AlertGroupRepo(db).create(name="test_group")
    exc = ExceptionDefRepo(db).create(severity=SeverityLevel.WARNING, group_id=group.id)
    event = SituationEventRepo(db).create(view_id=view.id, exception_id=exc.id)
    return user, event


class TestListAlerts:
    def test_list_alerts_empty(self, db):
        result = list_alerts(db)
        assert result["total"] == 0

    def test_list_alerts_has_entry(self, db, setup_alert_scenario):
        _user, _event = setup_alert_scenario
        result = list_alerts(db)
        assert result["total"] >= 1


class TestMarkHandled:
    def test_mark_handled_creates_review(self, db, setup_alert_scenario):
        user, event = setup_alert_scenario
        ok = mark_handled(db, event.id, user.id)
        assert ok is True

        reviews = AlertReviewRepo(db).all()
        assert len(reviews) == 1
        assert reviews[0].alert_id == event.id
        assert reviews[0].reviewer_id == user.id
        assert reviews[0].action == "handled"

    def test_mark_handled_nonexistent(self, db):
        ok = mark_handled(db, 99999, 1)
        assert ok is False


class TestMarkFalseAlarm:
    def test_mark_false_alarm_creates_review(self, db, setup_alert_scenario):
        user, event = setup_alert_scenario
        ok = mark_false_alarm(db, event.id, user.id)
        assert ok is True

        reviews = AlertReviewRepo(db).all()
        assert len(reviews) == 1
        assert reviews[0].action == "false_alarm"

    def test_mark_false_alarm_nonexistent(self, db):
        ok = mark_false_alarm(db, 99999, 1)
        assert ok is False
