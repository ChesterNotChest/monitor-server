"""AlertGroupRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.response_action_repo import ResponseActionRepo


class TestAlertGroupRepo:
    def test_create_and_get(self, db):
        repo = AlertGroupRepo(db)
        ag = repo.create(name="高优先级")
        assert ag.id is not None
        assert repo.get(ag.id).name == "高优先级"

    def test_delete(self, db):
        repo = AlertGroupRepo(db)
        ag = repo.create(name="低优先级")
        assert repo.delete(ag.id) is True

    def test_unique_name_violation(self, db):
        repo = AlertGroupRepo(db)
        repo.create(name="中优先级")
        with pytest.raises(IntegrityError):
            repo.create(name="中优先级")

    def test_with_responses_empty(self, db):
        repo = AlertGroupRepo(db)
        ag = repo.create(name="无响应分组")
        groups = repo.with_responses()
        found = [g for g in groups if g.id == ag.id]
        assert len(found) == 1
        assert found[0].responses == []

    def test_with_responses_populated(self, db):
        ag_repo = AlertGroupRepo(db)
        ra_repo = ResponseActionRepo(db)
        ag = ag_repo.create(name="有响应分组")
        ra = ra_repo.create(name="trigger_alarm")
        # Manual insert into association table
        from src.models.response_action import alert_group_responses
        db.execute(
            alert_group_responses.insert().values(group_id=ag.id, response_id=ra.id)
        )
        db.flush()
        groups = ag_repo.with_responses()
        found = [g for g in groups if g.id == ag.id]
        assert len(found) == 1
        assert len(found[0].responses) == 1
        assert found[0].responses[0].name == "trigger_alarm"
