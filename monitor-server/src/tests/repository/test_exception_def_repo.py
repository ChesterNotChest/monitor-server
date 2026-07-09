"""ExceptionDefRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.constants import SeverityLevel


class TestExceptionDefRepo:
    @pytest.fixture
    def alert_group(self, db):
        return AlertGroupRepo(db).create(name="异常测试分组")

    def test_create_and_get(self, db, alert_group):
        repo = ExceptionDefRepo(db)
        ed = repo.create(severity=SeverityLevel.CRITICAL, group_id=alert_group.id)
        assert ed.id is not None
        assert repo.get(ed.id).severity == SeverityLevel.CRITICAL

    def test_by_severity(self, db, alert_group):
        repo = ExceptionDefRepo(db)
        repo.create(severity=SeverityLevel.CRITICAL, group_id=alert_group.id)
        repo.create(severity=SeverityLevel.WARNING, group_id=alert_group.id)
        assert len(repo.by_severity(SeverityLevel.CRITICAL)) == 1
        assert len(repo.by_severity(SeverityLevel.INFO)) == 0

    def test_by_group(self, db, alert_group):
        repo = ExceptionDefRepo(db)
        ag2 = AlertGroupRepo(db).create(name="另一个分组")
        repo.create(severity=SeverityLevel.INFO, group_id=alert_group.id)
        repo.create(severity=SeverityLevel.WARNING, group_id=ag2.id)
        assert len(repo.by_group(alert_group.id)) == 1
        assert len(repo.by_group(ag2.id)) == 1

    def test_with_details(self, db, alert_group):
        repo = ExceptionDefRepo(db)
        repo.create(severity=SeverityLevel.EMERGENCY, group_id=alert_group.id)
        results = repo.with_details()
        assert len(results) == 1
        assert results[0].alert_group is not None
        assert results[0].entities == []
        assert results[0].actions == []
        assert results[0].sounds == []

    def test_delete(self, db, alert_group):
        repo = ExceptionDefRepo(db)
        ed = repo.create(severity=SeverityLevel.INFO, group_id=alert_group.id)
        assert repo.delete(ed.id) is True

    def test_fk_group_violation(self, db):
        repo = ExceptionDefRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(severity=SeverityLevel.WARNING, group_id=99999)
