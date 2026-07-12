"""ActionTypeRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.action_type_repo import ActionTypeRepo


class TestActionTypeRepo:
    def test_create_and_get(self, db):
        repo = ActionTypeRepo(db)
        at = repo.create(name="running")
        assert at.id is not None
        assert repo.get(at.id).name == "running"

    def test_delete(self, db):
        repo = ActionTypeRepo(db)
        at = repo.create(name="walking")
        assert repo.delete(at.id) is True

    def test_unique_name_violation(self, db):
        repo = ActionTypeRepo(db)
        repo.create(name="falling")
        with pytest.raises(IntegrityError):
            repo.create(name="falling")
