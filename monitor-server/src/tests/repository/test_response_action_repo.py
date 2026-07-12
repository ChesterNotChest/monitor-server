"""ResponseActionRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.response_action_repo import ResponseActionRepo
from src.repository.alert_group_repo import AlertGroupRepo


class TestResponseActionRepo:
    def test_create_and_get(self, db):
        repo = ResponseActionRepo(db)
        ra = repo.create(name="send_notification")
        assert ra.id is not None
        assert repo.get(ra.id).name == "send_notification"

    def test_delete(self, db):
        repo = ResponseActionRepo(db)
        ra = repo.create(name="trigger_recording")
        assert repo.delete(ra.id) is True

    def test_unique_name_violation(self, db):
        repo = ResponseActionRepo(db)
        repo.create(name="activate_alarm")
        with pytest.raises(IntegrityError):
            repo.create(name="activate_alarm")

    def test_with_groups(self, db):
        ra_repo = ResponseActionRepo(db)
        ag_repo = AlertGroupRepo(db)
        ra = ra_repo.create(name="call_api")
        ag = ag_repo.create(name="API告警组")
        from src.models.response_action import alert_group_responses
        db.execute(
            alert_group_responses.insert().values(group_id=ag.id, response_id=ra.id)
        )
        db.flush()
        actions = ra_repo.with_groups()
        found = [a for a in actions if a.id == ra.id]
        assert len(found) == 1
        assert len(found[0].alert_groups) == 1
        assert found[0].alert_groups[0].name == "API告警组"
